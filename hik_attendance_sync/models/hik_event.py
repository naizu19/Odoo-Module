from odoo import models, fields

class HikEvent(models.Model):
    _name = 'hik.event'
    _description = 'HikCentral Raw Event'
    _order = 'event_time desc'

    event_id = fields.Char(string='Event ID', required=True, index=True, copy=False)
    event_time = fields.Datetime(string='Event Time', required=True, index=True)
    employee_no = fields.Char(string='Employee ID', index=True)
    door_name = fields.Char(string='Door Name')
    event_type = fields.Integer(string='Event Type')
    processed = fields.Boolean(string='Processed', default=False)

    _sql_constraints = [
        ('event_id_unique', 'unique(event_id)', 'Event ID must be unique!')
    ]
