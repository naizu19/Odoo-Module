# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrShiftChangeRequest(models.Model):
    _name = 'hr.shift.change.request'
    _description = 'Shift Change Request'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'),
    )
    employee_id = fields.Many2one(
        'hr.employee', required=True, tracking=True,
        domain="[('company_id', 'in', allowed_company_ids)]",
    )
    company_id = fields.Many2one(
        related='employee_id.company_id', store=True, readonly=True,
    )
    department_id = fields.Many2one(
        related='employee_id.department_id', store=True, readonly=True,
    )
    current_shift_id = fields.Many2one(
        'hr.shift.template', string='Current Shift',
        compute='_compute_current_shift', store=True,
    )
    requested_shift_id = fields.Many2one(
        'hr.shift.template', string='Requested Shift', required=True, tracking=True,
        domain="[('company_id', '=', company_id)]",
    )
    date_from = fields.Date(string='Effective From', required=True, tracking=True)
    date_to = fields.Date(string='Effective To', required=True, tracking=True)
    requested_by = fields.Many2one(
        'res.users', string='Requested By',
        default=lambda self: self.env.user, readonly=True, tracking=True,
    )
    approver_id = fields.Many2one(
        'res.users', string='Approver', tracking=True,
        domain="[('share', '=', False)]",
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft', required=True, tracking=True,
    )
    notes = fields.Text(string='Reason')
    rejection_reason = fields.Text(string='Rejection Reason', tracking=True)
    assignment_id = fields.Many2one(
        'hr.shift.assignment', string='Created Assignment', readonly=True, copy=False,
    )
    can_approve = fields.Boolean(compute='_compute_can_approve')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.shift.change.request') or _('New')
            if not vals.get('approver_id'):
                company = self.env['res.company'].browse(
                    vals.get('company_id') or self.env.company.id
                )
                if company.shift_default_approver_id:
                    vals['approver_id'] = company.shift_default_approver_id.id
        return super().create(vals_list)

    @api.depends('employee_id', 'date_from')
    def _compute_current_shift(self):
        Assignment = self.env['hr.shift.assignment']
        for request in self:
            if request.employee_id and request.date_from:
                assignment = Assignment._get_assignment_for_date(
                    request.employee_id, request.date_from,
                )
                request.current_shift_id = assignment.shift_id if assignment else False
            else:
                request.current_shift_id = False

    @api.depends('approver_id', 'state')
    def _compute_can_approve(self):
        user = self.env.user
        for request in self:
            request.can_approve = (
                request.state == 'submitted'
                and (
                    user == request.approver_id
                    or user.has_group('advance_hr_shift_management.group_shift_officer')
                )
            )

    @api.constrains('date_from', 'date_to', 'requested_shift_id', 'employee_id')
    def _check_request(self):
        for request in self:
            if request.date_from and request.date_to and request.date_from > request.date_to:
                raise ValidationError(_('Effective end date must be on or after start date.'))
            if request.requested_shift_id and request.employee_id:
                if request.requested_shift_id.company_id != request.employee_id.company_id:
                    raise ValidationError(_('Requested shift must belong to the employee company.'))

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and not self.approver_id:
            company = self.employee_id.company_id
            if company.shift_default_approver_id:
                self.approver_id = company.shift_default_approver_id

    def action_submit(self):
        for request in self:
            if not request.approver_id:
                raise UserError(_('Please set an approver before submitting the request.'))
            if not request.approver_id.partner_id:
                raise UserError(_('The selected approver has no contact profile for email notifications.'))
            if request.requested_shift_id == request.current_shift_id:
                raise UserError(_('Requested shift is the same as the current shift.'))
            request.state = 'submitted'
            request._schedule_approval_activity()
            request.message_post(
                body=_('Shift change request submitted for approval.'),
                subtype_xmlid='mail.mt_comment',
            )
            request._send_shift_mail('advance_hr_shift_management.mail_template_shift_submit')

    def action_approve(self):
        for request in self:
            if not request.can_approve:
                raise UserError(_('You are not allowed to approve this request.'))
            assignment = request._create_assignment()
            request.write({
                'state': 'approved',
                'assignment_id': assignment.id,
            })
            request._regenerate_work_entries()
            request._done_approval_activities()
            request.message_post(
                body=_('Shift change approved. New assignment: %(name)s', name=assignment.name),
                subtype_xmlid='mail.mt_comment',
            )
            partners = request._get_approval_notify_partners()
            request._send_shift_mail(
                'advance_hr_shift_management.mail_template_shift_approved',
                partner_ids=partners.ids,
            )

    def action_reject(self):
        for request in self:
            if not request.can_approve:
                raise UserError(_('You are not allowed to reject this request.'))
            request.state = 'rejected'
            request._done_approval_activities()
            body = _('Shift change request rejected.')
            if request.rejection_reason:
                body = _('Shift change request rejected. Reason: %s', request.rejection_reason)
            request.message_post(body=body, subtype_xmlid='mail.mt_comment')
            partners = request._get_approval_notify_partners()
            request._send_shift_mail(
                'advance_hr_shift_management.mail_template_shift_rejected',
                partner_ids=partners.ids,
            )

    def action_cancel(self):
        for request in self.filtered(lambda r: r.state in ('draft', 'submitted')):
            was_submitted = request.state == 'submitted'
            request.state = 'cancelled'
            if was_submitted:
                request._done_approval_activities()
                request.message_post(
                    body=_('Shift change request cancelled.'),
                    subtype_xmlid='mail.mt_comment',
                )
                partners = request._get_cancel_notify_partners()
                request._send_shift_mail(
                    'advance_hr_shift_management.mail_template_shift_cancelled',
                    partner_ids=partners.ids,
                )

    def action_reset_draft(self):
        self.filtered(lambda r: r.state in ('rejected', 'cancelled')).write({'state': 'draft'})

    def _create_assignment(self):
        self.ensure_one()
        assignment = self.env['hr.shift.assignment'].sudo().create({
            'employee_id': self.employee_id.id,
            'shift_id': self.requested_shift_id.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'change_request_id': self.id,
            'state': 'draft',
        })
        assignment.sudo().action_activate()
        return assignment

    def _regenerate_work_entries(self):
        self.ensure_one()
        contract = self.employee_id.sudo().contract_id
        if contract and contract.work_entry_source == 'shift':
            contract.sudo()._recompute_work_entries(self.date_from, self.date_to)

    def _schedule_approval_activity(self):
        self.ensure_one()
        if self.approver_id:
            self.activity_schedule(
                'advance_hr_shift_management.mail_activity_shift_approval',
                user_id=self.approver_id.id,
                summary=_('Approve shift change for %s', self.employee_id.name),
            )

    def _done_approval_activities(self):
        activity_type = self.env.ref(
            'advance_hr_shift_management.mail_activity_shift_approval', raise_if_not_found=False,
        )
        if not activity_type:
            return
        for request in self:
            request.activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type
            ).action_feedback(feedback=_('Closed'))

    def _get_approval_notify_partners(self):
        """Partners to notify on approve/reject: requester + employee user."""
        self.ensure_one()
        partners = self.env['res.partner']
        if self.requested_by.partner_id:
            partners |= self.requested_by.partner_id
        if self.employee_id.user_id.partner_id:
            partners |= self.employee_id.user_id.partner_id
        elif self.employee_id.work_email:
            partner = self.env['res.partner'].sudo().search([
                ('email', '=', self.employee_id.work_email),
            ], limit=1)
            if partner:
                partners |= partner
        return partners

    def _get_cancel_notify_partners(self):
        """Partners to notify on cancel: requester + approver."""
        self.ensure_one()
        partners = self.env['res.partner']
        if self.requested_by.partner_id:
            partners |= self.requested_by.partner_id
        if self.approver_id.partner_id:
            partners |= self.approver_id.partner_id
        return partners

    def _send_shift_mail(self, template_xmlid, partner_ids=None):
        """Send email using a mail template; skip silently if mail is not configured."""
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            return
        for request in self:
            if partner_ids is not None and not partner_ids:
                continue
            email_values = {}
            if partner_ids:
                email_values['recipient_ids'] = [(6, 0, partner_ids)]
            try:
                template.send_mail(
                    request.id,
                    force_send=False,
                    email_values=email_values,
                    email_layout_xmlid='mail.mail_notification_layout',
                )
            except Exception:
                request.message_post(
                    body=_('Could not send email notification. Please check your outgoing mail server.'),
                    subtype_xmlid='mail.mt_comment',
                )
