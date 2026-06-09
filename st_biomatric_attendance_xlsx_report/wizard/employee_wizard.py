# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools import formataddr
from odoo.tools.mail import email_normalize

_logger = logging.getLogger(__name__)


class EmployeeAttendanceMailWizard(models.TransientModel):
    _name = 'employee.custom.wizard'
    _description = 'Send attendance XLSX by email'

    year = fields.Integer(string="Year", default=lambda self: int(fields.Date.today().year))
    month = fields.Selection([
        ('January', 'January'), ('February', 'February'), ('March', 'March'),
        ('April', 'April'), ('May', 'May'), ('June', 'June'),
        ('July', 'July'), ('August', 'August'), ('September', 'September'),
        ('October', 'October'), ('November', 'November'), ('December', 'December')
    ], string="Month", default=lambda self: fields.Date.today().strftime('%B'))

    report_header = fields.Char(string="Report Header", default="PMMS")

    cc_employee_ids = fields.Many2many(
        'hr.employee', string="CC Employees",
        help="Select employees to send a copy of the email"
    )

    def _attendance_mail_from(self):
        """Stable From address for SMTP (avoid bare login / invalid addresses)."""
        self.ensure_one()
        user = self.env.user
        partner = user.partner_id
        for candidate in (
            partner.email,
            getattr(user, 'email', None),
            user.login if user.login and '@' in user.login else None,
        ):
            if candidate and email_normalize(candidate, strict=False):
                name = partner.name or user.name or self.env.company.name or 'Odoo'
                return formataddr((name, email_normalize(candidate, strict=False) or candidate.strip()))
        company = self.env.company
        if company.email and email_normalize(company.email, strict=False):
            return formataddr((company.name or 'Company', email_normalize(company.email, strict=False)))
        raise UserError(
            _(
                'Cannot send email: set an email on your user profile or on the company (%s), '
                'or use a login that is a full email address.'
            )
            % (company.display_name,)
        )

    def _employee_recipient_email(self, employee):
        for addr in (employee.work_email, getattr(employee, 'private_email', None)):
            if addr and email_normalize(addr, strict=False):
                return email_normalize(addr, strict=False)
            if addr and '@' in addr:
                return addr.strip()
        return ''

    def send_email(self):
        self.ensure_one()
        Mail = self.env['mail.mail'].sudo()
        Attachment = self.env['ir.attachment'].sudo()

        active_ids = self.env.context.get('active_ids', [])
        employees = self.env['hr.employee'].browse(active_ids)
        if not employees:
            raise UserError(_('No employees selected.'))

        cc_emails = []
        for e in self.cc_employee_ids:
            addr = self._employee_recipient_email(e)
            if addr:
                cc_emails.append(addr)

        mail_from = self._attendance_mail_from()
        sent_count = 0
        skipped_no_email = []

        for emp in employees:
            to_addr = self._employee_recipient_email(emp)
            if not to_addr:
                skipped_no_email.append(emp.display_name)
                continue

            report_wizard = self.env['individual.attendance.report.wizard'].create({
                'employee_id': emp.id,
                'month': self.month,
                'year': self.year,
                'report_header': self.report_header,
            })
            report_wizard.with_context(skip_attendance_report_action=True).export_individual_employee_report()
            report_wizard.invalidate_recordset(['report_file', 'report_name'])
            data_b64 = report_wizard.report_file
            fname = (report_wizard.report_name or 'attendance_report.xlsx').strip()
            if not fname.lower().endswith('.xlsx'):
                fname += '.xlsx'

            if not data_b64:
                _logger.warning(
                    'Attendance email: empty report for employee %s (id=%s)',
                    emp.display_name, emp.id,
                )
                skipped_no_email.append('%s (empty report)' % emp.display_name)
                continue

            att = Attachment.create({
                'name': fname,
                'datas': data_b64,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'type': 'binary',
            })

            employee_name = emp.name or ''
            project_name = self.report_header or 'N/A'
            location_name = emp.work_location_id.name or 'Head Office'
            period = "%s/%s" % (self.year, self.month)

            body_html = """
<div style="border:1px solid #ccc; padding:15px; font-family:Arial, sans-serif; font-size:14px; direction:rtl; text-align:right;">
    <h3 style="color:#004080;">تقرير الحضور والانصراف للموظف</h3>
    <p><b>الاسم:</b> %(name)s <br/>
       <b>المشروع:</b> %(project)s <br/>
       <b>الموقع:</b> %(location)s <br/>
       <b>الفترة:</b> %(period)s</p>
    <br/><br/><br/>
    <p>يرجى الاطلاع على المرفق لتقرير التفصيلي.</p>
    <p>Please see the attached document for the detailed report.</p>
    <div style="text-align:right; direction:rtl; font-weight:bold; margin-top:20px;">
        <b>تحياتي</b> / Regards
    </div>
</div>
""" % {
                'name': employee_name,
                'project': project_name,
                'location': location_name,
                'period': period,
            }

            mail = Mail.create({
                'subject': '%s (%s/%s) - تقرير الحضور' % (employee_name, self.month, self.year),
                'body_html': body_html,
                'email_to': to_addr,
                'email_cc': ','.join(cc_emails) if cc_emails else False,
                'email_from': mail_from,
                'attachment_ids': [(6, 0, att.ids)],
            })
            mail.send()
            sent_count += 1

        parts = []
        if sent_count:
            parts.append(_('%s email(s) sent.') % sent_count)
        if skipped_no_email:
            parts.append(
                _('Skipped (no work/private email or empty report): %s')
                % ', '.join(skipped_no_email[:20])
            )
            if len(skipped_no_email) > 20:
                parts.append(_('…and more.'))

        msg = ' '.join(parts) if parts else _('No emails were sent.')
        msg_type = 'success' if sent_count else 'warning'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Attendance report email'),
                'message': msg,
                'type': msg_type,
                'sticky': bool(skipped_no_email),
            },
        }
