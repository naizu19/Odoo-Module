# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    shift_default_approver_id = fields.Many2one(
        'res.users', string='Default Shift Approver',
        domain="[('share', '=', False)]",
    )
    shift_grace_period_minutes = fields.Integer(
        string='Shift Grace Period (minutes)', default=15,
        help='Minutes of tolerance before marking attendance as late.',
    )
