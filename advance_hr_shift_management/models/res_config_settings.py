# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    shift_default_approver_id = fields.Many2one(
        related='company_id.shift_default_approver_id', readonly=False,
    )
    shift_grace_period_minutes = fields.Integer(
        related='company_id.shift_grace_period_minutes', readonly=False,
    )
