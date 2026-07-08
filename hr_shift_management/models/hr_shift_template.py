# -*- coding: utf-8 -*-

from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrShiftTemplate(models.Model):
    _name = 'hr.shift.template'
    _description = 'Shift Template'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company,
    )
    start_hour = fields.Float(
        string='Start Hour', required=True, default=8.0,
        help='Start time as float hours (e.g. 8.0 = 08:00, 18.5 = 18:30).',
    )
    end_hour = fields.Float(
        string='End Hour', required=True, default=17.0,
        help='End time as float hours. For overnight shifts use a value less than start hour and enable Crosses Midnight.',
    )
    crosses_midnight = fields.Boolean(
        string='Crosses Midnight',
        help='Enable when the shift ends on the next calendar day (e.g. 18:00 to 02:00).',
    )
    break_duration = fields.Integer(
        string='Break (minutes)', default=0,
        help='Unpaid break duration deducted from worked hours.',
    )
    color = fields.Integer(string='Color', default=0)
    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', string='Work Entry Type',
        domain="['|', ('country_id', '=', False), ('country_id', '=', company_country_id)]",
    )
    company_country_id = fields.Many2one(
        related='company_id.country_id', string='Company Country',
    )
    work_monday = fields.Boolean(default=True)
    work_tuesday = fields.Boolean(default=True)
    work_wednesday = fields.Boolean(default=True)
    work_thursday = fields.Boolean(default=True)
    work_friday = fields.Boolean(default=True)
    work_saturday = fields.Boolean(default=False)
    work_sunday = fields.Boolean(default=False)
    duration_hours = fields.Float(
        string='Duration (hours)', compute='_compute_duration_hours', store=True,
    )
    display_time = fields.Char(compute='_compute_display_time')

    WEEKDAY_FIELDS = [
        'work_monday', 'work_tuesday', 'work_wednesday',
        'work_thursday', 'work_friday', 'work_saturday', 'work_sunday',
    ]

    @api.depends('start_hour', 'end_hour', 'crosses_midnight', 'break_duration')
    def _compute_duration_hours(self):
        for shift in self:
            shift.duration_hours = shift._raw_duration_hours()

    @api.depends('start_hour', 'end_hour', 'crosses_midnight')
    def _compute_display_time(self):
        for shift in self:
            start = shift._format_hour(shift.start_hour)
            end = shift._format_hour(shift.end_hour)
            suffix = ' (+1 day)' if shift.crosses_midnight else ''
            shift.display_time = f'{start} – {end}{suffix}'

    @api.constrains('start_hour', 'end_hour', 'crosses_midnight')
    def _check_hours(self):
        for shift in self:
            if shift.start_hour < 0 or shift.start_hour >= 24:
                raise ValidationError(_('Start hour must be between 0 and 24.'))
            if shift.end_hour < 0 or shift.end_hour > 24:
                raise ValidationError(_('End hour must be between 0 and 24.'))
            if not shift.crosses_midnight and shift.end_hour <= shift.start_hour:
                raise ValidationError(
                    _('End hour must be after start hour, or enable Crosses Midnight for overnight shifts.')
                )
            if shift.crosses_midnight and shift.end_hour >= shift.start_hour:
                raise ValidationError(
                    _('For overnight shifts, end hour must be less than start hour (e.g. 18:00 to 02:00).')
                )

    @api.constrains(*WEEKDAY_FIELDS)
    def _check_working_days(self):
        for shift in self:
            if not any(shift[f] for f in self.WEEKDAY_FIELDS):
                raise ValidationError(_('At least one working day must be selected for the shift.'))

    @api.onchange('start_hour', 'end_hour')
    def _onchange_hours_crosses_midnight(self):
        if self.end_hour < self.start_hour:
            self.crosses_midnight = True

    def _raw_duration_hours(self):
        self.ensure_one()
        if self.crosses_midnight:
            gross = (24.0 - self.start_hour) + self.end_hour
        else:
            gross = self.end_hour - self.start_hour
        return max(gross - (self.break_duration / 60.0), 0.0)

    @api.model
    def _format_hour(self, hour_float):
        hours = int(hour_float)
        minutes = int(round((hour_float - hours) * 60))
        if minutes == 60:
            hours += 1
            minutes = 0
        return f'{hours:02d}:{minutes:02d}'

    def _float_to_time(self, hour_float):
        hours = int(hour_float)
        minutes = int(round((hour_float - hours) * 60))
        if minutes == 60:
            hours += 1
            minutes = 0
        hours = hours % 24
        return time(hours, minutes)

    def works_on_weekday(self, weekday):
        """Return True if shift applies on weekday (0=Monday .. 6=Sunday)."""
        self.ensure_one()
        field_name = self.WEEKDAY_FIELDS[weekday]
        return self[field_name]

    def get_interval_for_date(self, target_date, tz_name):
        """Return (start_utc, end_utc) aware datetimes for a shift on target_date."""
        self.ensure_one()
        tz = pytz.timezone(tz_name or 'UTC')
        start_time = self._float_to_time(self.start_hour)
        start_local = tz.localize(datetime.combine(target_date, start_time))

        if self.crosses_midnight:
            end_date = target_date + timedelta(days=1)
            end_time = self._float_to_time(self.end_hour)
        else:
            end_date = target_date
            end_hour = self.end_hour if self.end_hour < 24 else 0
            if self.end_hour >= 24:
                end_date = target_date + timedelta(days=1)
            end_time = self._float_to_time(end_hour)

        end_local = tz.localize(datetime.combine(end_date, end_time))
        if end_local <= start_local:
            end_local += timedelta(days=1)

        return start_local.astimezone(pytz.utc), end_local.astimezone(pytz.utc)

    def get_break_interval_for_date(self, target_date, tz_name):
        """Return break interval in the middle of the shift if break_duration is set."""
        self.ensure_one()
        if not self.break_duration:
            return None
        start_utc, end_utc = self.get_interval_for_date(target_date, tz_name)
        total_seconds = (end_utc - start_utc).total_seconds()
        break_seconds = self.break_duration * 60
        if break_seconds >= total_seconds:
            return None
        mid = start_utc + timedelta(seconds=(total_seconds - break_seconds) / 2)
        return mid, mid + timedelta(seconds=break_seconds)
