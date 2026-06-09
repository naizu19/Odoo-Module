# -*- coding: utf-8 -*-
{
    'name': 'Biometric Attendance XLSX Reports',
    'version': '17.0.2.3',
    'category': 'Human Resources',
    'sequence': 1,
    'author': 'NK-Solutions',
    'summary': 'Generate professional departmental and individual employee monthly attendance reports in styled XLSX/Excel format.',
    'description': """
Biometric Attendance XLSX Reports Engine
========================================
This module allows HR managers and administrators to extract automated, highly organized, and executive-ready attendance reports in Excel (.xlsx) format directly from Odoo.

Key Features:
-------------
* **Departmental Attendance Sheets:** Export a consolidated monthly attendance view for all employees or specific departments (with sub-departments support).
* **Individual Employee Reports:** Isolate an individual employee's log structured cleanly into dynamic horizontal 7-day weekly blocks (Week 1 to Week 5).
* **Advanced IN/OUT/TOTAL Logic:** Captures the earliest punch as check-in and the latest punch as check-out while displaying total daily durations.
* **Overnight / Night Shift Support:** Automatically calculates accurate durations using timedeltas for shifts crossing midnight boundaries.
* **Executive Formatting:** Features clean hexadecimal corporate color schemes, cell border lines, text wraps, and auto-adjusting dates.
* **Multilingual Notes & Legend:** Includes standard colored visual status tables (Red, Orange, Light Green, Yellow) with localized Arabic text remarks at the bottom.
* **In-Memory Compilation:** Built using specialized in-memory RAM streams (BytesIO) to guarantee fast generation without draining server disk space resources.

Tested with biometric sync logs and standard corporate payroll verification loops.
    """,
    'price': 100.00,
    'currency': 'USD',
    'license': 'OPL-1',
    'depends': [
        'hr_attendance',
        'hik_attendance_sync',
        'hr'
    ],
    'data': [
        'security/ir_model_access.xml',
        'views/attendance_xlsx_menus.xml',
        'views/inherit_employee_view.xml',
        'wizard/employee_wizard.xml',
        'wizard/department_attendance_report_wizard.xml',
        'wizard/individual_employee_report_wizard.xml',
    ],
    'images': [
        'static/description/banner.png'  # ایپ اسٹور پر ڈسپلے ہونے والا مین بینر
    ],
    'installable': True,
    'application': True,  # اسے True کر دیا ہے کیونکہ یہ ایک مین بزنس ایپلی کیشن / فیچر ماڈیول ہے
    'auto_install': False,
}