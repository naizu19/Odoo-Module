from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PayslipPaymentWizard(models.TransientModel):
    _name = "payslip.payment.wizard"
    _description = "Selective Payslip Payment Wizard"

    line_ids = fields.One2many('payslip.payment.line', 'wizard_id', string='Payment Lines')
    journal_id = fields.Many2one(
        'account.journal',
        string='Payment Journal',
        required=True,
        domain=[('type', 'in', ('bank', 'cash'))]
    )
    payment_date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.context_today
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        batch = self.env['hr.payslip.run'].browse(self._context.get('active_id'))
        payslips = batch.slip_ids.filtered(lambda s: s.state in ('done', 'partial'))

        line_vals = []
        for p in payslips:
            due = p.get_due_amount()
            paid = p.total_paid_amount
            remain = p.get_remaining_amount()
            if remain > 0:
                line_vals.append((0, 0, {
                    'select': True,
                    'payslip_id': p.id,
                    'employee_id': p.employee_id.id,
                    'due_amount': due,
                    'already_paid': paid,
                    'remaining': remain,
                    'payment_amount': remain,  # default to remaining
                }))
        res['line_ids'] = line_vals
        return res

    def action_confirm_payment(self):
        selected_lines = self.line_ids.filtered(lambda l: l.select)
        if not selected_lines:
            raise UserError(_("Please select at least one payslip to pay."))

        for line in selected_lines:
            payslip = line.payslip_id
            pay = abs(line.payment_amount)
            if pay <= 0:
                continue

            remain_before = payslip.get_remaining_amount()
            if pay > remain_before:
                raise ValidationError(
                    _("You cannot pay more than remaining balance for %s.\nRemaining: %.2f")
                    % (payslip.name, remain_before)
                )

            net_rule = payslip.struct_id.rule_ids.filtered(lambda r: r.code == 'NET')
            if not net_rule or not net_rule[0].account_credit:
                raise ValidationError(
                    _("Please configure a Credit Account for NET Salary rule in structure '%s'.") %
                    payslip.struct_id.name
                )

            debit_account = net_rule[0].account_credit.id
            credit_account = self.journal_id.default_account_id.id

            move_vals = {
                'journal_id': self.journal_id.id,
                'date': self.payment_date,
                'ref': payslip.number or payslip.name,
                'line_ids': [
                    (0, 0, {
                        'name': payslip.name or payslip.number or 'Payslip Payment',
                        'debit': pay,
                        'credit': 0.0,
                        'account_id': debit_account,
                        'partner_id': payslip.employee_id.work_contact_id.id,
                    }),
                    (0, 0, {
                        'name': payslip.name or payslip.number or 'Payslip Payment',
                        'debit': 0.0,
                        'credit': pay,
                        'account_id': credit_account,
                        'partner_id': payslip.employee_id.work_contact_id.id,
                    }),
                ],
            }
            move = self.env['account.move'].sudo().create(move_vals)
            move.action_post()

            # update totals
            payslip.total_paid_amount += pay

            # determine state
            if payslip.total_paid_amount >= payslip.get_due_amount():
                payslip.state = 'paid'
            else:
                payslip.state = 'partial'

        return {'type': 'ir.actions.act_window_close'}


class PayslipPaymentLine(models.TransientModel):
    _name = 'payslip.payment.line'
    _description = 'Payslip Payment Line'

    select = fields.Boolean(string='Select', default=True)
    wizard_id = fields.Many2one('payslip.payment.wizard', ondelete='cascade')
    payslip_id = fields.Many2one('hr.payslip', string='Payslip', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', related='payslip_id.employee_id', store=True)
    due_amount = fields.Monetary(string='Total Due', currency_field='currency_id', readonly=True)
    already_paid = fields.Monetary(string='Already Paid', currency_field='currency_id', readonly=True)
    remaining = fields.Monetary(string='Remaining', currency_field='currency_id', readonly=True)
    payment_amount = fields.Monetary(string='Payment Amount', currency_field='currency_id')
    currency_id = fields.Many2one(related='payslip_id.currency_id', store=True, readonly=True)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    state = fields.Selection(
        selection_add=[('partial', 'Partially Paid')],
        ondelete={'partial': 'set done'}
    )
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        related='company_id.currency_id',
        store=True,
        readonly=True
    )
    total_paid_amount = fields.Monetary(
        string="Total Paid Amount",
        currency_field='currency_id',
        default=0.0
    )

    def get_due_amount(self):
        """Return total NET amount of payslip."""
        net = self.line_ids.filtered(lambda l: l.code == 'NET')
        return abs(net.total) if net else 0.0

    def get_remaining_amount(self):
        """Return remaining unpaid balance."""
        return max(0.0, self.get_due_amount() - self.total_paid_amount)

    @api.model
    def _setup_fields(self):
        """Ensure 'partial' is always included in state selection."""
        super()._setup_fields()
        state_field = self._fields.get('state')
        if state_field and 'partial' not in dict(state_field.selection):
            state_field.selection.append(('partial', 'Partially Paid'))