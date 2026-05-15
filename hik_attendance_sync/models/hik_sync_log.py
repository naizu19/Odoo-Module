from odoo import models, fields

class HikSyncLog(models.Model):
    _name = 'hik.sync.log'
    _description = 'HikCentral Sync Log'
    _order = 'create_date desc'

    name = fields.Char(string='Action', default="Cron Job Execution")
    status = fields.Selection([('success', 'Success'), ('error', 'Error')], string='Status')
    message = fields.Text(string='Sync Summary')
    events_found = fields.Integer(string='Events Found')
    attendance_created = fields.Integer(string='Attendance Records Created')
    error_details = fields.Text(string='Error Details')
    execution_time = fields.Float(string='Execution Time (ms)', digits=(12, 2))
    request_payload = fields.Text(string='Request Payload')
    response_data = fields.Text(string='Response Data')
