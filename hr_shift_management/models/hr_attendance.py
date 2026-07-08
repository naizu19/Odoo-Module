# -*- coding: utf-8 -*-

from datetime import timedelta

import pytz

from odoo import api, fields, models, _


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    shift_id = fields.Many2one(
        'hr.shift.template', string='Assigned Shift',
        compute='_compute_shift_fields', store=True,
    )
    shift_assignment_id = fields.Many2one(
        'hr.shift.assignment', string='Shift Assignment',
        compute='_compute_shift_fields', store=True,
    )
    is_late = fields.Boolean(
        string='Late', compute='_compute_shift_fields', store=True,
    )
    late_minutes = fields.Float(
        string='Late (minutes)', compute='_compute_shift_fields', store=True,
    )

    @api.depends('check_in', 'employee_id')
    def _compute_shift_fields(self):
        for attendance in self:
            attendance.shift_id = False
            attendance.shift_assignment_id = False
            attendance.is_late = False
            attendance.late_minutes = 0.0
            if not attendance.check_in or not attendance.employee_id:
                continue
            employee = attendance.employee_id
            if not employee._uses_shift_work_entries():
                continue
            tz_name = employee._get_shift_tz()
            check_in_utc = attendance.check_in
            if check_in_utc.tzinfo is None:
                check_in_utc = pytz.utc.localize(check_in_utc)
            local_check_in = check_in_utc.astimezone(pytz.timezone(tz_name))
            target_date = local_check_in.date()
            assignment = self.env['hr.shift.assignment']._get_assignment_for_date(
                employee, target_date,
            )
            if not assignment:
                continue
            attendance.shift_assignment_id = assignment.id
            attendance.shift_id = assignment.shift_id.id
            shift_start, shift_end = assignment.shift_id.get_interval_for_date(
                target_date, tz_name,
            )
            grace = timedelta(minutes=employee.company_id.shift_grace_period_minutes or 0)
            if check_in_utc > shift_start + grace:
                attendance.is_late = True
                attendance.late_minutes = (check_in_utc - shift_start).total_seconds() / 60.0
