# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class HrShiftAssignment(models.Model):
    _inherit = 'hr.shift.assignment'

    @api.model
    def _count_assignments_in_period(self, date_from, date_to, company_ids):
        return self.search_count([
            ('state', 'in', ['active', 'expired']),
            ('date_from', '<=', date_to),
            ('date_to', '>=', date_from),
            ('company_id', 'in', company_ids),
        ])

    @api.model
    def get_dashboard_data(self):
        today = fields.Date.context_today(self)
        company_ids = self.env.companies.ids
        user = self.env.user

        Assignment = self.env['hr.shift.assignment']
        ChangeRequest = self.env['hr.shift.change.request']
        Attendance = self.env['hr.attendance']
        ShiftTemplate = self.env['hr.shift.template']

        today_assignments = Assignment.search([
            ('state', '=', 'active'),
            ('date_from', '<=', today),
            ('date_to', '>=', today),
            ('company_id', 'in', company_ids),
        ])

        pending_requests = ChangeRequest.search([
            ('state', '=', 'submitted'),
            ('company_id', 'in', company_ids),
        ], order='create_date desc', limit=6)

        pending_count = ChangeRequest.search_count([
            ('state', '=', 'submitted'),
            ('company_id', 'in', company_ids),
        ])

        month_start = today.replace(day=1)
        last_month_end = month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        month_total = Assignment._count_assignments_in_period(month_start, today, company_ids)
        last_month_total = Assignment._count_assignments_in_period(
            last_month_start, last_month_end, company_ids,
        )
        if last_month_total:
            growth_pct = round((month_total - last_month_total) / last_month_total * 100)
        else:
            growth_pct = 100 if month_total else 0

        month_requests = ChangeRequest.search([
            ('create_date', '>=', datetime.combine(month_start, datetime.min.time())),
            ('company_id', 'in', company_ids),
        ])
        approved_count = len(month_requests.filtered(lambda r: r.state == 'approved'))
        total_requests_month = len(month_requests)
        approval_rate = round(approved_count / total_requests_month * 100) if total_requests_month else 0

        monthly_chart = []
        for i in range(2, -1, -1):
            m_start = (month_start - relativedelta(months=i))
            m_end = (m_start + relativedelta(months=1)) - timedelta(days=1)
            if i == 0:
                m_end = today
            count = Assignment._count_assignments_in_period(m_start, m_end, company_ids)
            monthly_chart.append({
                'label': m_start.strftime('%b'),
                'count': count,
            })
        max_bar = max((m['count'] for m in monthly_chart), default=1) or 1
        for m in monthly_chart:
            m['height'] = round(m['count'] / max_bar * 100)

        employee_ids = today_assignments.employee_id.ids
        today_start = datetime.combine(today, datetime.min.time())
        today_end = today_start + timedelta(days=1)

        attendances_today = Attendance.search([
            ('employee_id', 'in', employee_ids),
            ('check_in', '>=', today_start),
            ('check_in', '<', today_end),
        ]) if employee_ids else Attendance

        present_ids = set(attendances_today.mapped('employee_id').ids)
        late_count = len(attendances_today.filtered('is_late'))

        donut_colors = ['#22c55e', '#f97316', '#6366f1', '#3b82f6', '#ef4444', '#ec4899']
        shift_stats = defaultdict(int)
        shift_type_meta = {}
        for assignment in today_assignments:
            shift_stats[assignment.shift_id.name] += 1
            if assignment.shift_id.name not in shift_type_meta:
                shift_type_meta[assignment.shift_id.name] = {
                    'is_night': assignment.shift_id.crosses_midnight,
                }

        total_today = len(today_assignments) or 1
        shift_distribution = []
        for idx, (name, count) in enumerate(sorted(shift_stats.items(), key=lambda x: -x[1])):
            shift_distribution.append({
                'name': name,
                'count': count,
                'percent': round(count / total_today * 100),
                'color': donut_colors[idx % len(donut_colors)],
                'is_night': shift_type_meta[name]['is_night'],
            })

        roster = []
        for assignment in today_assignments.sorted(key=lambda a: (a.shift_id.start_hour, a.employee_id.name)):
            emp = assignment.employee_id
            att = attendances_today.filtered(lambda a, e=emp: a.employee_id == e)[:1]
            if att and att.is_late:
                status = 'late'
                status_label = _('Late')
            elif emp.id in present_ids:
                status = 'confirmed'
                status_label = _('Confirmed')
            else:
                status = 'pending'
                status_label = _('Pending')
            roster.append({
                'assignment_id': assignment.id,
                'employee_name': emp.name,
                'role': emp.job_id.name or _('Employee'),
                'department': assignment.department_id.name or '—',
                'shift_name': assignment.shift_id.name,
                'shift_time': assignment.shift_id.display_time,
                'shift_type': _('Night') if assignment.shift_id.crosses_midnight else _('Onsite'),
                'is_night': assignment.shift_id.crosses_midnight,
                'status': status,
                'status_label': status_label,
                'date_label': fields.Date.to_string(today),
                'check_in': att.check_in.strftime('%H:%M') if att and att.check_in else False,
            })

        pending_list = [{
            'id': req.id,
            'name': req.name,
            'employee_name': req.employee_id.name,
            'shift_name': req.requested_shift_id.name,
            'date_from': fields.Date.to_string(req.date_from),
            'date_to': fields.Date.to_string(req.date_to),
        } for req in pending_requests]

        return {
            'today': fields.Date.to_string(today),
            'user_name': user.name.split()[0] if user.name else _('User'),
            'kpis': {
                'month_total': month_total,
                'growth_pct': growth_pct,
                'approved_count': approved_count,
                'total_requests_month': total_requests_month,
                'approval_rate': approval_rate,
                'on_shift_today': len(today_assignments),
                'present_today': len(present_ids),
                'late_today': late_count,
                'pending_approvals': pending_count,
                'active_shifts': ShiftTemplate.search_count([
                    ('active', '=', True), ('company_id', 'in', company_ids),
                ]),
            },
            'monthly_chart': monthly_chart,
            'roster': roster,
            'pending_approvals': pending_list,
            'shift_distribution': shift_distribution,
            'permissions': {
                'is_officer': user.has_group('advance_hr_shift_management.group_shift_officer'),
                'is_manager': user.has_group('advance_hr_shift_management.group_shift_manager'),
            },
        }

    @api.model
    def get_dashboard_action(self, xmlid):
        action = self.env.ref(xmlid, raise_if_not_found=False)
        if not action:
            return False
        return action.sudo()._get_action_dict()
