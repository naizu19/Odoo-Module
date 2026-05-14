from odoo import models, fields

class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    check_in_device = fields.Char(string='Check-in Device')
    check_out_device = fields.Char(string='Check-out Device')
