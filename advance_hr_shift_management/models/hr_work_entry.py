# -*- coding: utf-8 -*-

from odoo import fields, models


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    shift_assignment_id = fields.Many2one(
        'hr.shift.assignment', string='Shift Assignment', ondelete='set null',
        index=True,
    )
