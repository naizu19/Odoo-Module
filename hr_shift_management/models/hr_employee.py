# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz
from pytz import timezone

from odoo import fields, models
from odoo.addons.resource.models.utils import Intervals, timezone_datetime


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    shift_assignment_ids = fields.One2many(
        'hr.shift.assignment', 'employee_id', string='Shift Assignments',
        groups='hr.group_hr_user',
    )
    current_shift_assignment_id = fields.Many2one(
        'hr.shift.assignment', compute='_compute_current_shift_assignment',
        string='Current Shift', groups='hr.group_hr_user',
    )
    current_shift_id = fields.Many2one(
        related='current_shift_assignment_id.shift_id', string='Current Shift Template',
        groups='hr.group_hr_user',
    )

    def _compute_current_shift_assignment(self):
        today = fields.Date.context_today(self)
        Assignment = self.env['hr.shift.assignment']
        for employee in self:
            employee.current_shift_assignment_id = Assignment._get_assignment_for_date(
                employee, today,
            )

    def _uses_shift_work_entries(self):
        self.ensure_one()
        contract = self.contract_id
        return bool(contract and contract.work_entry_source == 'shift')

    def _get_shift_for_date(self, target_date):
        self.ensure_one()
        assignment = self.env['hr.shift.assignment']._get_assignment_for_date(self, target_date)
        return assignment.shift_id if assignment else False

    def _get_shift_tz(self):
        self.ensure_one()
        return self.tz or self.company_id.resource_calendar_id.tz or 'UTC'

    def _get_shift_attendance_intervals(self, start, stop, lunch=False):
        """Return Intervals of expected work time from shift assignments."""
        self.ensure_one()
        if not self._uses_shift_work_entries():
            return super()._employee_attendance_intervals(start, stop, lunch=lunch)

        start = timezone_datetime(start)
        stop = timezone_datetime(stop)
        date_from = start.astimezone(pytz.utc).date()
        date_to = stop.astimezone(pytz.utc).date()
        assignments = self.env['hr.shift.assignment']._get_assignments_for_period(
            self, date_from, date_to,
        )
        tz_name = self._get_shift_tz()
        interval_list = []
        for assignment in assignments.filtered(lambda a: a.employee_id == self):
            if lunch:
                current = max(assignment.date_from, date_from)
                end_date = min(assignment.date_to, date_to)
                while current <= end_date:
                    if assignment.shift_id.works_on_weekday(current.weekday()):
                        break_interval = assignment.shift_id.get_break_interval_for_date(
                            current, tz_name,
                        )
                        if break_interval:
                            b_start, b_end = break_interval
                            if b_end > start and b_start < stop:
                                interval_list.append((
                                    max(b_start, start), min(b_end, stop), assignment.shift_id,
                                ))
                    current += timedelta(days=1)
            else:
                for i_start, i_end, record in assignment.get_intervals_for_period(start, stop, tz_name):
                    interval_list.append((i_start, i_end, record))
        return Intervals(interval_list)

    def _employee_attendance_intervals(self, start, stop, lunch=False):
        shift_employees = self.filtered(lambda e: e._uses_shift_work_entries())
        if not shift_employees:
            return super()._employee_attendance_intervals(start, stop, lunch=lunch)
        if len(shift_employees) == 1 and shift_employees == self:
            return shift_employees._get_shift_attendance_intervals(start, stop, lunch=lunch)
        result = Intervals()
        for employee in self:
            if employee in shift_employees:
                result |= employee._get_shift_attendance_intervals(start, stop, lunch=lunch)
            else:
                result |= super(HrEmployee, employee)._employee_attendance_intervals(
                    start, stop, lunch=lunch,
                )
        return result

    def _get_expected_attendances(self, date_from, date_to):
        if self._uses_shift_work_entries():
            return self._get_shift_attendance_intervals(date_from, date_to, lunch=False)
        return super()._get_expected_attendances(date_from, date_to)

    def _get_work_days_data_batch(self, from_datetime, to_datetime, compute_leaves=True, calendar=None, domain=None):
        shift_employees = self.filtered(lambda e: e._uses_shift_work_entries())
        regular_employees = self - shift_employees
        result = {}
        if regular_employees:
            result.update(super(HrEmployee, regular_employees)._get_work_days_data_batch(
                from_datetime, to_datetime,
                compute_leaves=compute_leaves, calendar=calendar, domain=domain,
            ))
        if not shift_employees:
            return result

        from_datetime = timezone_datetime(from_datetime)
        to_datetime = timezone_datetime(to_datetime)
        for employee in shift_employees:
            intervals = employee._get_shift_attendance_intervals(from_datetime, to_datetime, lunch=False)
            lunch_intervals = employee._get_shift_attendance_intervals(from_datetime, to_datetime, lunch=True)
            if lunch_intervals:
                intervals = intervals - lunch_intervals
            if compute_leaves and domain is not False:
                leave_domain = domain or [('time_type', '=', 'leave')]
                calendar_obj = employee.resource_calendar_id or employee.company_id.resource_calendar_id
                if calendar_obj:
                    leaves = calendar_obj._leave_intervals_batch(
                        from_datetime, to_datetime, employee.resource_id, leave_domain,
                    )
                    intervals = intervals - leaves[employee.resource_id.id]
            total_seconds = sum(
                (stop - start).total_seconds() for start, stop, _meta in intervals
            )
            hours = total_seconds / 3600.0
            avg_hours = employee.company_id.resource_calendar_id.hours_per_day if employee.company_id.resource_calendar_id else 8.0
            days = hours / avg_hours if avg_hours else 0.0
            result[employee.id] = {'days': days, 'hours': hours}
        return result

    def _list_work_time_per_day(self, from_datetime, to_datetime, calendar=None, domain=None):
        shift_employees = self.filtered(lambda e: e._uses_shift_work_entries())
        regular_employees = self - shift_employees
        result = {}
        if regular_employees:
            result.update(super(HrEmployee, regular_employees)._list_work_time_per_day(
                from_datetime, to_datetime, calendar=calendar, domain=domain,
            ))
        if not shift_employees:
            return result

        from_datetime = timezone_datetime(from_datetime)
        to_datetime = timezone_datetime(to_datetime)
        for employee in shift_employees:
            tz_name = employee._get_shift_tz()
            employee_tz = timezone(tz_name)
            record_result = defaultdict(float)
            current_date = from_datetime.astimezone(employee_tz).date()
            end_date = to_datetime.astimezone(employee_tz).date()
            while current_date <= end_date:
                day_start = employee_tz.localize(datetime.combine(current_date, time.min)).astimezone(pytz.utc)
                day_end = employee_tz.localize(
                    datetime.combine(current_date + timedelta(days=1), time.min)
                ).astimezone(pytz.utc)
                intervals = employee._get_shift_attendance_intervals(
                    max(from_datetime, day_start), min(to_datetime, day_end), lunch=False,
                )
                seconds = sum((stop - start).total_seconds() for start, stop, _m in intervals)
                if seconds:
                    record_result[current_date] += seconds / 3600.0
                current_date += timedelta(days=1)
            result[employee.id] = sorted(record_result.items())
        return result

    def get_shift_interval_for_date(self, target_date):
        """Public helper: return (start_utc, end_utc) for employee shift on a date."""
        self.ensure_one()
        shift = self._get_shift_for_date(target_date)
        if not shift:
            return None
        return shift.get_interval_for_date(target_date, self._get_shift_tz())
