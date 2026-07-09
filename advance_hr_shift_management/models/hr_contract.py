# -*- coding: utf-8 -*-

from collections import defaultdict

import pytz

from odoo import fields, models
from odoo.addons.hr_work_entry_contract.models.hr_work_intervals import WorkIntervals


class HrContract(models.Model):
    _inherit = 'hr.contract'

    work_entry_source = fields.Selection(
        selection_add=[('shift', 'Shift Assignments')],
        ondelete={'shift': 'set default'},
    )

    def _get_more_vals_attendance_interval(self, interval):
        result = super()._get_more_vals_attendance_interval(interval)
        if interval[2]._name == 'hr.shift.assignment':
            assignment = interval[2]
            result.append(('shift_assignment_id', assignment.id))
        return result

    def _get_interval_work_entry_type(self, interval):
        if interval[2]._name == 'hr.shift.assignment':
            assignment = interval[2]
            if assignment.shift_id.work_entry_type_id:
                return assignment.shift_id.work_entry_type_id
        return super()._get_interval_work_entry_type(interval)

    def _get_attendance_intervals(self, start_dt, end_dt):
        shift_contracts = self.filtered(lambda c: c.work_entry_source == 'shift')
        if not shift_contracts:
            return super()._get_attendance_intervals(start_dt, end_dt)

        employees = shift_contracts.employee_id
        date_from = start_dt.astimezone(pytz.utc).date()
        date_to = end_dt.astimezone(pytz.utc).date()
        assignments = self.env['hr.shift.assignment']._get_assignments_for_period(
            employees, date_from, date_to,
        )

        intervals = defaultdict(list)
        for assignment in assignments:
            employee = assignment.employee_id
            tz_name = employee._get_tz()
            for interval_start, interval_end, record in assignment.get_intervals_for_period(
                start_dt, end_dt, tz_name,
            ):
                intervals[employee.resource_id.id].append((
                    interval_start, interval_end, record,
                ))

        mapped_intervals = {
            resource_id: WorkIntervals(interval_list)
            for resource_id, interval_list in intervals.items()
        }
        for contract in shift_contracts:
            resource_id = contract.employee_id.resource_id.id
            mapped_intervals.setdefault(resource_id, WorkIntervals())
        non_shift_contracts = self - shift_contracts
        if non_shift_contracts:
            mapped_intervals.update(
                super(HrContract, non_shift_contracts)._get_attendance_intervals(start_dt, end_dt)
            )
        return mapped_intervals

    def _get_lunch_intervals(self, start_dt, end_dt):
        shift_contracts = self.filtered(lambda c: c.work_entry_source == 'shift')
        if not shift_contracts:
            return super()._get_lunch_intervals(start_dt, end_dt)

        employees = shift_contracts.employee_id
        date_from = start_dt.astimezone(pytz.utc).date()
        date_to = end_dt.astimezone(pytz.utc).date()
        assignments = self.env['hr.shift.assignment']._get_assignments_for_period(
            employees, date_from, date_to,
        )

        from datetime import timedelta

        intervals = defaultdict(list)
        for assignment in assignments:
            employee = assignment.employee_id
            tz_name = employee._get_tz()
            current = max(assignment.date_from, date_from)
            end_date = min(assignment.date_to, date_to)
            while current <= end_date:
                if assignment.shift_id.works_on_weekday(current.weekday()):
                    break_interval = assignment.shift_id.get_break_interval_for_date(current, tz_name)
                    if break_interval:
                        break_start, break_end = break_interval
                        if break_end > start_dt and break_start < end_dt:
                            intervals[employee.resource_id.id].append((
                                max(break_start, start_dt),
                                min(break_end, end_dt),
                                assignment.shift_id,
                            ))
                current += timedelta(days=1)

        result = {
            resource_id: WorkIntervals(interval_list)
            for resource_id, interval_list in intervals.items()
        }
        non_shift_contracts = self - shift_contracts
        if non_shift_contracts:
            result.update(super(HrContract, non_shift_contracts)._get_lunch_intervals(start_dt, end_dt))
        return result
