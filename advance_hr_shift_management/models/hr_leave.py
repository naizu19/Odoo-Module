# -*- coding: utf-8 -*-

from odoo import models


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        shift_leaves = self.filtered(
            lambda l: l.employee_id and l.employee_id._uses_shift_work_entries()
        )
        if not shift_leaves:
            return super()._get_durations(
                check_leave_type=check_leave_type, resource_calendar=resource_calendar,
            )
        result = super()._get_durations(
            check_leave_type=check_leave_type, resource_calendar=resource_calendar,
        )
        for leave in shift_leaves:
            if not leave.date_from or not leave.date_to:
                continue
            work_data = leave.employee_id._get_work_days_data_batch(
                leave.date_from, leave.date_to,
                compute_leaves=not leave.holiday_status_id.include_public_holidays_in_duration,
            )
            hours = work_data.get(leave.employee_id.id, {}).get('hours', 0.0)
            days = work_data.get(leave.employee_id.id, {}).get('days', 0.0)
            if leave.request_unit_hours:
                result[leave.id] = (days, hours)
            else:
                calendar = resource_calendar or leave.resource_calendar_id
                hours_per_day = calendar.hours_per_day if calendar else 8.0
                if hours_per_day:
                    days = hours / hours_per_day
                result[leave.id] = (days, hours)
        return result
