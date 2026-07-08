# -*- coding: utf-8 -*-

from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrShiftAssignment(models.Model):
    _name = 'hr.shift.assignment'
    _description = 'Shift Assignment'
    _order = 'date_from desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one(
        'hr.employee', required=True, ondelete='cascade', tracking=True,
        domain="[('company_id', 'in', allowed_company_ids)]",
    )
    shift_id = fields.Many2one(
        'hr.shift.template', required=True, ondelete='restrict', tracking=True,
        domain="[('company_id', '=', company_id)]",
    )
    company_id = fields.Many2one(
        related='employee_id.company_id', store=True, readonly=True,
    )
    department_id = fields.Many2one(
        related='employee_id.department_id', store=True, readonly=True,
    )
    date_from = fields.Date(required=True, tracking=True)
    date_to = fields.Date(required=True, tracking=True)
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('expired', 'Expired'),
        ],
        default='draft', required=True, tracking=True,
    )
    change_request_id = fields.Many2one(
        'hr.shift.change.request', string='Change Request', ondelete='set null',
        copy=False,
    )
    shift_display_time = fields.Char(related='shift_id.display_time')

    @api.depends('employee_id', 'shift_id', 'date_from', 'date_to')
    def _compute_name(self):
        for assignment in self:
            if assignment.employee_id and assignment.shift_id:
                assignment.name = _(
                    '%(employee)s — %(shift)s (%(start)s → %(end)s)',
                    employee=assignment.employee_id.name,
                    shift=assignment.shift_id.name,
                    start=assignment.date_from,
                    end=assignment.date_to,
                )
            else:
                assignment.name = _('New Shift Assignment')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for assignment in self:
            if assignment.date_from and assignment.date_to and assignment.date_from > assignment.date_to:
                raise ValidationError(_('End date must be on or after start date.'))

    @api.constrains('employee_id', 'date_from', 'date_to', 'state')
    def _check_no_overlap(self):
        for assignment in self.filtered(lambda a: a.state in ('draft', 'active')):
            overlapping = self.search([
                ('id', '!=', assignment.id),
                ('employee_id', '=', assignment.employee_id.id),
                ('state', 'in', ('draft', 'active')),
                ('date_from', '<=', assignment.date_to),
                ('date_to', '>=', assignment.date_from),
            ])
            if overlapping:
                raise ValidationError(_(
                    'Shift assignment overlaps with existing assignment "%(name)s" for %(employee)s.',
                    name=overlapping[0].name,
                    employee=assignment.employee_id.name,
                ))

    def action_activate(self):
        for assignment in self:
            assignment._expire_overlapping()
            assignment.state = 'active'
        return True

    def action_expire(self):
        self.write({'state': 'expired'})
        return True

    def _expire_overlapping(self):
        self.ensure_one()
        overlapping = self.search([
            ('id', '!=', self.id),
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'active'),
            ('date_from', '<=', self.date_to),
            ('date_to', '>=', self.date_from),
        ])
        for other in overlapping:
            if other.date_from < self.date_from:
                other.write({
                    'date_to': self.date_from - timedelta(days=1),
                })
                if other.date_to < other.date_from:
                    other.state = 'expired'
            else:
                other.state = 'expired'

    @api.model
    def _get_assignment_for_date(self, employee, target_date):
        """Return the active shift assignment covering target_date for employee."""
        return self.search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'active'),
            ('date_from', '<=', target_date),
            ('date_to', '>=', target_date),
        ], limit=1, order='date_from desc')

    @api.model
    def _get_assignments_for_period(self, employees, date_from, date_to):
        """Return assignments active in [date_from, date_to] for given employees."""
        return self.search([
            ('employee_id', 'in', employees.ids),
            ('state', '=', 'active'),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
        ])

    @api.model
    def _cron_expire_assignments(self):
        today = fields.Date.context_today(self)
        expired = self.search([
            ('state', '=', 'active'),
            ('date_to', '<', today),
        ])
        expired.write({'state': 'expired'})

    def get_intervals_for_period(self, start_dt, end_dt, tz_name):
        """Build shift intervals for this assignment within [start_dt, end_dt]."""
        self.ensure_one()
        from datetime import datetime
        import pytz

        intervals = []
        current = self.date_from
        end_date = self.date_to
        utc = pytz.utc
        start_dt = start_dt.astimezone(utc) if start_dt.tzinfo else utc.localize(start_dt)
        end_dt = end_dt.astimezone(utc) if end_dt.tzinfo else utc.localize(end_dt)

        while current <= end_date:
            if self.shift_id.works_on_weekday(current.weekday()):
                interval_start, interval_end = self.shift_id.get_interval_for_date(current, tz_name)
                if interval_end > start_dt and interval_start < end_dt:
                    intervals.append((
                        max(interval_start, start_dt),
                        min(interval_end, end_dt),
                        self,
                    ))
            current += timedelta(days=1)
        return intervals
