{
    'name': 'HikCentral  Attendance Integration  ',
    'version': '19.0.1.0.0',
    'summary': 'Real-time synchronization between HikCentral Professional and Odoo Attendance via OpenAPI Webhooks and Cron.',
    'description': """
HikCentral Professional Attendance Integration
==============================================
Seamlessly bridge your Hikvision hardware with Odoo HR Attendance. 
This module leverages the high-performance HikCentral OpenAPI to ensure 
your attendance data is accurate, real-time, and automated.

Key Features:
-------------
* **Real-time Sync:** Uses Webhooks (Subscribed Events) for instant check-in/out updates.
* **Smart Filtering:** Filter events by Door Index Codes and Authentication modes (Face, Fingerprint, Card).
* **Duplicate Prevention:** Advanced logic to prevent multiple scans from creating duplicate Odoo records.
* **Manual Override:** One-click "Sync Attendance" button for historical data recovery.
* **Detailed Auditing:** Full logs of every API call and raw event data for security compliance..
* **Automated Cron:** Background heartbeat sync to ensure no data is lost during network downtime.....


    """,
    'category': 'Human Resources/Attendances',
    'website': '',
    'author': 'NK-Solutions',
    'depends': [
        'hr_attendance',
        'base'

    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/hik_config_views.xml',
        'views/hik_sync_log_views.xml',
        'views/hik_event_views.xml',
        'views/hr_attendance_views.xml',
        'views/hr_employee_views.xml',
    ],
    'images': [
        'static/description/banner.gif',

        'static/description/install.png',
        'static/description/config.png',
        'static/description/menu.png',
        'static/description/config.mp4',
        'static/description/icon.png',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'price': 200.00,
    'currency': 'USD',
    'license': 'OPL-1',
}