{
    'name': 'Hr Shift Management',
    'version': '18.0.0.0.0',
    'category': 'Human Resources',
    'sequence': 215,
    'summary': 'Shift scheduling, approval workflow, dashboard & payroll integration',
    'description': """
Shift Management
================

Complete employee shift scheduling for Odoo 18 with approval workflow,
executive dashboard, email notifications, and HR integrations.

**Key Features**
----------------
* Shift templates with midnight-cross support (e.g. 18:00 – 02:00 +1 day)
* Employee shift assignments with overlap protection
* Change request workflow: Draft → Submitted → Approved / Rejected / Cancelled
* Email notifications to approver, requester, and employee
* Modern executive dashboard with KPIs, charts, and quick actions
* Attendance late detection with configurable grace period
* Time off duration based on assigned shift hours
* Payroll integration via Shift Assignments or Attendances work entry source

**Menus**
---------
Dashboard · Shifts · Assignments · Change Requests · Regenerate Work Entries

See README.md and static/description/index.html for full documentation.
    """,
    'author': 'NK-Solutions',
    'license': 'OPL-1',
    'price': 300.00,
    'currency': 'USD',
    'images': [
        'static/description/banner.png',
        'static/description/screenshot_dashboard.png',
        'static/description/screenshot_shifts.png',
        'static/description/screenshot_assignments.png',
        'static/description/screenshot_change_requests.png',
        'static/description/screenshot_approval_email.png',
    ],
    'depends': [
        'hr',
        'hr_contract',
        'hr_attendance',
        'hr_work_entry_contract',
        'hr_holidays',
        'mail',
    ],
    'data': [
        'security/hr_shift_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_activity_type_data.xml',
        'data/mail_template_data.xml',
        'views/hr_shift_template_views.xml',
        'views/hr_shift_assignment_views.xml',
        'views/hr_shift_change_request_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_attendance_views.xml',
        'views/hr_contract_views.xml',
        'views/res_config_settings_views.xml',
        'views/shift_dashboard_views.xml',
        'views/menus.xml',
        'wizard/shift_work_entry_regenerate_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'advance_hr_shift_management/static/src/dashboard/shift_dashboard.scss',
            'advance_hr_shift_management/static/src/dashboard/shift_dashboard.xml',
            'advance_hr_shift_management/static/src/dashboard/shift_dashboard.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
