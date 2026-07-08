# -*- coding: utf-8 -*-

from datetime import date, datetime, timedelta

import pytz

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged('post_install', '-at_install', 'shift_management')
class TestShiftManagement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.tz = 'Asia/Karachi'
        cls.company = cls.env.company

        cls.approver = new_test_user(
            cls.env, login='shift_approver',
            groups='hr_shift_management.group_shift_approver,hr.group_hr_user',
        )
        cls.manager = new_test_user(
            cls.env, login='shift_manager',
            groups='hr_shift_management.group_shift_manager,hr.group_hr_user',
        )
        cls.manager_employee = cls.env['hr.employee'].create({
            'name': 'Shift Manager',
            'user_id': cls.manager.id,
        })
        cls.company.write({'shift_default_approver_id': cls.approver.id})

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Shift Employee ABC',
            'tz': 'Asia/Karachi',
            'parent_id': cls.manager_employee.id,
        })
        cls.calendar = cls.env.ref('resource.resource_calendar_std')
        cls.contract = cls.env['hr.contract'].create({
            'name': 'Shift Contract',
            'employee_id': cls.employee.id,
            'wage': 50000,
            'date_start': date(2025, 1, 1),
            'state': 'open',
            'resource_calendar_id': cls.calendar.id,
            'work_entry_source': 'shift',
        })
        cls.employee.contract_id = cls.contract

        cls.morning_shift = cls.env['hr.shift.template'].create({
            'name': 'Morning',
            'start_hour': 8.0,
            'end_hour': 17.0,
            'break_duration': 60,
            'company_id': cls.company.id,
        })
        cls.evening_shift = cls.env['hr.shift.template'].create({
            'name': 'Evening',
            'start_hour': 18.0,
            'end_hour': 2.0,
            'crosses_midnight': True,
            'company_id': cls.company.id,
        })
        cls.afternoon_shift = cls.env['hr.shift.template'].create({
            'name': 'Afternoon',
            'start_hour': 14.0,
            'end_hour': 24.0,
            'company_id': cls.company.id,
        })

    def test_night_shift_interval_crosses_midnight(self):
        target = date(2025, 6, 2)  # Monday
        start_utc, end_utc = self.evening_shift.get_interval_for_date(target, 'Asia/Karachi')
        self.assertLess(start_utc, end_utc)
        duration_hours = (end_utc - start_utc).total_seconds() / 3600
        self.assertAlmostEqual(duration_hours, 8.0, places=1)

        karachi = pytz.timezone('Asia/Karachi')
        start_local = start_utc.astimezone(karachi)
        end_local = end_utc.astimezone(karachi)
        self.assertEqual(start_local.hour, 18)
        self.assertEqual(end_local.day, target.day + 1)
        self.assertEqual(end_local.hour, 2)

    def test_shift_duration_hours(self):
        self.assertAlmostEqual(self.morning_shift.duration_hours, 8.0, places=1)
        self.assertAlmostEqual(self.evening_shift.duration_hours, 8.0, places=1)
        self.assertAlmostEqual(self.afternoon_shift.duration_hours, 10.0, places=1)

    def test_assignment_overlap_constraint(self):
        assignment = self.env['hr.shift.assignment'].create({
            'employee_id': self.employee.id,
            'shift_id': self.morning_shift.id,
            'date_from': date(2025, 6, 1),
            'date_to': date(2025, 6, 7),
            'state': 'active',
        })
        with self.assertRaises(ValidationError):
            self.env['hr.shift.assignment'].create({
                'employee_id': self.employee.id,
                'shift_id': self.evening_shift.id,
                'date_from': date(2025, 6, 5),
                'date_to': date(2025, 6, 12),
                'state': 'active',
            })
        assignment.action_expire()

    def test_change_request_approval_workflow(self):
        self.env['hr.shift.assignment'].create({
            'employee_id': self.employee.id,
            'shift_id': self.morning_shift.id,
            'date_from': date(2025, 6, 1),
            'date_to': date(2025, 6, 7),
            'state': 'active',
        })
        request = self.env['hr.shift.change.request'].with_user(self.manager).create({
            'employee_id': self.employee.id,
            'requested_shift_id': self.evening_shift.id,
            'date_from': date(2025, 6, 8),
            'date_to': date(2025, 6, 14),
            'approver_id': self.approver.id,
            'notes': 'Weekly rotation',
        })
        self.assertEqual(request.state, 'draft')
        request.with_user(self.manager).action_submit()
        self.assertEqual(request.state, 'submitted')
        request.with_user(self.approver).action_approve()
        self.assertEqual(request.state, 'approved')
        self.assertTrue(request.assignment_id)
        self.assertEqual(request.assignment_id.shift_id, self.evening_shift)
        self.assertEqual(request.assignment_id.state, 'active')

    def test_work_entry_intervals_from_shift(self):
        self.env['hr.shift.assignment'].create({
            'employee_id': self.employee.id,
            'shift_id': self.morning_shift.id,
            'date_from': date(2025, 6, 2),
            'date_to': date(2025, 6, 6),
            'state': 'active',
        })
        start_dt = pytz.utc.localize(datetime(2025, 6, 2, 0, 0))
        end_dt = pytz.utc.localize(datetime(2025, 6, 7, 0, 0))
        intervals = self.contract._get_attendance_intervals(start_dt, end_dt)
        resource_intervals = intervals[self.employee.resource_id.id]
        self.assertTrue(resource_intervals)
        self.assertEqual(len(list(resource_intervals)), 5)

    def test_attendance_late_detection(self):
        self.env['hr.shift.assignment'].create({
            'employee_id': self.employee.id,
            'shift_id': self.morning_shift.id,
            'date_from': date(2025, 6, 2),
            'date_to': date(2025, 6, 2),
            'state': 'active',
        })
        karachi = pytz.timezone('Asia/Karachi')
        check_in = karachi.localize(datetime(2025, 6, 2, 8, 20)).astimezone(pytz.utc).replace(tzinfo=None)
        attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': check_in,
        })
        self.assertTrue(attendance.is_late)
        self.assertGreater(attendance.late_minutes, 0)

    def test_leave_duration_uses_shift_hours(self):
        self.env['hr.shift.assignment'].create({
            'employee_id': self.employee.id,
            'shift_id': self.morning_shift.id,
            'date_from': date(2025, 6, 2),
            'date_to': date(2025, 6, 6),
            'state': 'active',
        })
        karachi = pytz.timezone('Asia/Karachi')
        start_dt = karachi.localize(datetime(2025, 6, 2, 0, 0))
        end_dt = karachi.localize(datetime(2025, 6, 3, 0, 0))
        work_data = self.employee._get_work_days_data_batch(
            start_dt, end_dt, compute_leaves=False,
        )
        self.assertAlmostEqual(work_data[self.employee.id]['hours'], 8.0, places=1)

    def test_monthly_shift_rotation(self):
        """Simulate 4 weekly shift changes across a month."""
        weeks = [
            (self.morning_shift, date(2025, 6, 2), date(2025, 6, 8)),
            (self.evening_shift, date(2025, 6, 9), date(2025, 6, 15)),
            (self.afternoon_shift, date(2025, 6, 16), date(2025, 6, 22)),
            (self.morning_shift, date(2025, 6, 23), date(2025, 6, 29)),
        ]
        Assignment = self.env['hr.shift.assignment']
        for shift, start, end in weeks:
            assignment = Assignment.create({
                'employee_id': self.employee.id,
                'shift_id': shift.id,
                'date_from': start,
                'date_to': end,
                'state': 'draft',
            })
            assignment.action_activate()

        start_dt = pytz.utc.localize(datetime(2025, 6, 2, 0, 0))
        end_dt = pytz.utc.localize(datetime(2025, 6, 30, 0, 0))
        intervals = self.contract._get_attendance_intervals(start_dt, end_dt)
        resource_intervals = list(intervals[self.employee.resource_id.id])
        self.assertGreaterEqual(len(resource_intervals), 20)

        work_data = self.employee._get_work_days_data_batch(start_dt, end_dt, compute_leaves=False)
        self.assertGreater(work_data[self.employee.id]['hours'], 0)
