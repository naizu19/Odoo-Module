# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ShiftWorkEntryRegenerateWizard(models.TransientModel):
    _name = 'shift.work.entry.regenerate.wizard'
    _description = 'Regenerate Shift Work Entries'

    date_from = fields.Date(string='From', required=True)
    date_to = fields.Date(string='To', required=True)
    employee_ids = fields.Many2many(
        'hr.employee', string='Employees', required=True,
        domain="[('company_id', 'in', allowed_company_ids)]",
    )

    def action_regenerate(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise ValidationError(_('End date must be on or after start date.'))
        contracts = self.employee_ids.mapped('contract_id').filtered(
            lambda c: c.work_entry_source == 'shift' and c.state in ('open', 'close'),
        )
        if not contracts:
            raise ValidationError(_('No active shift-based contracts found for selected employees.'))
        wizard = self.env['hr.work.entry.regeneration.wizard'].create({
            'employee_ids': [(6, 0, self.employee_ids.ids)],
            'date_from': self.date_from,
            'date_to': self.date_to,
        })
        wizard.with_context(work_entry_skip_validation=True).regenerate_work_entries()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Work Entries Regenerated'),
                'message': _('Work entries have been regenerated for the selected period.'),
                'type': 'success',
                'sticky': False,
            },
        }
