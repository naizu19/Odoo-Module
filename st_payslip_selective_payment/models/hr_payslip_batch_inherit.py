from odoo import models, fields


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    state = fields.Selection(selection_add=[('partial', 'Partially Paid')])

    def open_payment_wizard(self):
        return {
            'name': 'Selective Payslip Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'payslip.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payslip_ids': [(6, 0, self.slip_ids.filtered(lambda s: s.state == 'done' and not s.paid).ids)]
            }
        }
