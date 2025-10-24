{
    'name': 'Selective Payslip Payment (Partial / Full)',
    'version': '17.0.1.0.0',
    'summary': 'Make full or partial payments for payslips with ease.',
    'description': """
Selective Payslip Payment
=========================
This module allows HR or Accounting departments to make **selective or partial payments** of employee payslips directly from the payslip batch.

✅ Key Features:
----------------
- Select payslips to pay (full or partial)
- Automatically records accounting entries
- Prevents double payment
- Updates payslip state to "Partially Paid" or "Paid"
- Shows total paid and remaining balance per employee
- Journal & payment date configurable
- Supports multi-company and multi-currency environments
- Fully compatible with Odoo 17 Enterprise

💼 Ideal for:
-------------
- HR Payroll Managers
- Finance & Accounting Teams
- Multi-company organizations
    """,
    'author': 'Saudi-Tech',
    'website': 'https://saudi-tech.com.sa/',
    'maintainer': 'Aftab Khan',
    'license': 'OPL-1',
    'price': 12.0,
    'currency': 'USD',
    'category': 'Human Resources/Payroll',
    'depends': ['hr_payroll', 'account', 'hr_payroll_expense'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_payslip_batch_inherit.xml',
        'wizards/payslip_payment_wizard_view.xml'
    ],
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
