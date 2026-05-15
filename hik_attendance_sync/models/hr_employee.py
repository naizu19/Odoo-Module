from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_no = fields.Char(string="Employee No", index=True)