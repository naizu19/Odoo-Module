from odoo import models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def action_open_attendance_report_mail_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'employee.custom.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': self._name,
                'active_ids': self.ids,
            },
        }
