from calendar import monthrange
from odoo import models, fields
from datetime import datetime, timedelta
import io
import base64
import xlsxwriter
import calendar


class IndividualAttendanceReportWizard(models.TransientModel):
    _name = 'individual.attendance.report.wizard'
    _description = 'Individual attendance XLSX export'

    is_printed = fields.Boolean(string="Is Printed", default=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        required=True)
    month = fields.Selection([
        ('January', 'January'), ('February', 'February'), ('March', 'March'),
        ('April', 'April'), ('May', 'May'), ('June', 'June'),
        ('July', 'July'), ('August', 'August'), ('September', 'September'),
        ('October', 'October'), ('November', 'November'), ('December', 'December')
    ], string="Month", required=True, default=lambda self: datetime.now().strftime('%B'))

    year = fields.Integer(string="Year", required=True, default=lambda self: int(datetime.now().strftime('%Y')))

    report_header = fields.Char(string="Report Header", required=True, default="PMMS")

    report_file = fields.Binary(string="Report File")
    report_name = fields.Char(string="File Name")

    def export_individual_employee_report(self):
        month_index = list(calendar.month_name).index(self.month)
        days_in_month = calendar.monthrange(int(self.year), month_index)[1]

        safe_name = (self.employee_id.name or 'employee').replace('/', '-')
        file_name = f"Attendance_{safe_name}_{self.month}_{self.year}.xlsx"

        fp = io.BytesIO()
        workbook = xlsxwriter.Workbook(fp, {'in_memory': True})
        worksheet = workbook.add_worksheet("Report")

        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#D3D3D3', 'border': 2, 'text_wrap': True,
        })
        id_name_format = workbook.add_format({
            'bold': True, 'align': 'top', 'valign': 'vtop', 'indent': 1,
            'border': 1, 'text_wrap': True
        })
        data_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True
        })
        week_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 2, 'text_wrap': True,
            'bg_color': '#D3D3D3',
        })
        total_data_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'bg_color': '#ADD8E6',
        })
        project_format = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'bg_color': '#DFFFD6', 'border': 1, 'bold': True, 'text_wrap': True
        })
        arabic_format = workbook.add_format({'bold': True, 'font_name': 'Arial', 'font_size': 14})

        worksheet.set_row(0, 40)
        header_text = self.report_header or "PMMS"
        sheet_title = "MONTH ATTENDANCE SHEET"

        worksheet.merge_range('A1:F1', header_text, project_format)
        worksheet.merge_range('G1:H1', f"YEAR\n{self.year}", project_format)
        worksheet.merge_range('I1:J1', f"MONTH\n{self.month}", project_format)
        worksheet.merge_range('K1:M1', sheet_title, header_format)

        worksheet.write('A2', 'ID', header_format)
        worksheet.merge_range('B2:D2', 'NAME', header_format)
        worksheet.merge_range('E2:F2', '', week_format)
        worksheet.merge_range('E3:F3', 'IN/OUT/TOTAL', header_format)
        worksheet.merge_range('E4:F4', 'IN', header_format)
        worksheet.merge_range('E5:F5', 'OUT', header_format)
        worksheet.merge_range('E6:F6', 'TOTAL', header_format)
        worksheet.merge_range('E7:F7', '', week_format)
        worksheet.merge_range('E8:F8', 'IN/OUT/TOTAL', header_format)
        worksheet.merge_range('E9:F9', 'IN', header_format)
        worksheet.merge_range('E10:F10', 'OUT', header_format)
        worksheet.merge_range('E11:F11', 'TOTAL', header_format)
        worksheet.merge_range('E12:F12', '', week_format)
        worksheet.merge_range('E13:F13', 'IN/OUT/TOTAL', header_format)
        worksheet.merge_range('E14:F14', 'IN', header_format)
        worksheet.merge_range('E15:F15', 'OUT', header_format)
        worksheet.merge_range('E16:F16', 'TOTAL', header_format)
        worksheet.merge_range('E17:F17', '', week_format)
        worksheet.merge_range('E18:F18', 'IN/OUT/TOTAL', header_format)
        worksheet.merge_range('E19:F19', 'IN', header_format)
        worksheet.merge_range('E20:F20', 'OUT', header_format)
        worksheet.merge_range('E21:F21', 'TOTAL', header_format)
        worksheet.merge_range('E22:F22', '', week_format)
        worksheet.merge_range('E23:F23', 'IN/OUT/TOTAL', header_format)
        worksheet.merge_range('E24:F24', 'IN', header_format)
        worksheet.merge_range('E25:F25', 'OUT', header_format)
        worksheet.merge_range('E26:F26', 'TOTAL', header_format)
        worksheet.set_row(26, 50)
        worksheet.merge_range('E27:F27', 'TOTAL WORKING TIME', header_format)

        worksheet.set_row(2, 40)
        worksheet.set_row(7, 40)
        worksheet.set_row(12, 40)
        worksheet.set_row(17, 40)
        worksheet.set_row(22, 40)

        emp_id = getattr(self.employee_id, "employee_no", False) or self.employee_id.id
        emp_name_email = f"{self.employee_id.name}\n{self.employee_id.work_email or ''}"

        start_row = 2
        end_row = 26
        emp_id_text = "    \n" + str(emp_id)
        emp_name_email_text = "\n" + emp_name_emaila

        worksheet.merge_range(start_row, 0, end_row, 0, emp_id_text, id_name_format)
        worksheet.merge_range(start_row, 1, end_row, 3, emp_name_email_text, id_name_format)

        daily_logs = {}
        start_date = datetime(int(self.year), month_index, 1)
        end_date = datetime(int(self.year), month_index, days_in_month, 23, 59, 59)

        logs = self.env['hik.attendance.log'].search([
            ('employee_id', '=', self.employee_id.id),
            ('attendance_date', '>=', start_date.date()),
            ('attendance_date', '<=', end_date.date()),
        ], order='attendance_date asc, event_time asc')
        for log in logs:
            dt_in = fields.Datetime.context_timestamp(self, log.event_time)
            dt_out = fields.Datetime.context_timestamp(self, log.last_event_time) if log.last_event_time else None
            punches = [dt_in]
            if dt_out:
                punches.append(dt_out)
            daily_logs[dt_in.day] = daily_logs.get(dt_in.day, []) + punches

        current_day = 1
        current_row = 1
        col_start = 6
        week_number = 1

        while current_day <= days_in_month:
            worksheet.merge_range(current_row, col_start, current_row, col_start + 6, f"Week {week_number}", week_format)
            current_row += 1
            week_days = []
            for i in range(7):
                if current_day > days_in_month:
                    break
                day_date = datetime(int(self.year), month_index, current_day)
                date_text = f"{day_date.strftime('%A')}\n{current_day}-{self.month[:3]}-{self.year}"
                worksheet.write(current_row, col_start + i, date_text, week_format)
                worksheet.set_column(col_start + i, col_start + i, 12)
                week_days.append(current_day)
                current_day += 1
            current_row += 1
            for r_offset, label in enumerate(["IN", "OUT", "TOTAL"]):
                for i, day_index in enumerate(week_days):
                    if day_index > days_in_month:
                        continue
                    punches = daily_logs.get(day_index, [])
                    has_checkout = len(punches) >= 2 and punches[-1] != punches[0]
                    in_val = punches[0].strftime("%H.%M") if punches else ''
                    out_val = punches[-1].strftime("%H.%M") if has_checkout else '00'
                    total_val = ''
                    if has_checkout:
                        try:
                            in_dt = punches[0]
                            out_dt = punches[-1]
                            if out_dt < in_dt:
                                out_dt += timedelta(days=1)
                            total_val = str(out_dt - in_dt).split('.')[0]
                        except Exception:
                            total_val = ''
                    val = in_val if label == "IN" else (out_val if label == "OUT" else total_val)
                    cell_format = data_format if label in ["IN", "OUT"] else total_data_format
                    worksheet.write(current_row + r_offset, col_start + i, val, cell_format)

            current_row += 3
            week_number += 1

        total_work_seconds = 0
        for _day, punches in daily_logs.items():
            if len(punches) >= 2 and punches[-1] != punches[0]:
                in_dt = punches[0]
                out_dt = punches[-1]
                if out_dt < in_dt:
                    out_dt += timedelta(days=1)
                total_work_seconds += (out_dt - in_dt).total_seconds()

        total_hours = int(total_work_seconds // 3600)
        total_minutes = int((total_work_seconds % 3600) // 60)
        total_time_str = f"{total_hours}.{total_minutes:02d}"
        worksheet.write('G27', total_time_str, total_data_format)

        worksheet.merge_range('H27:M27', "ملاحظات", arabic_format)

        red_box = workbook.add_format({'bg_color': '#FF0000'})
        orange_box = workbook.add_format({'bg_color': '#FFA500'})
        light_green_box = workbook.add_format({'bg_color': '#90EE90'})
        yellow_box = workbook.add_format({'bg_color': '#FFFF00'})
        worksheet.set_column('F:F', 3)
        worksheet.set_row(28, 20)
        worksheet.set_row(29, 20)
        worksheet.set_row(30, 20)
        worksheet.set_row(31, 20)
        worksheet.write('F29', '', red_box)
        worksheet.write('F30', '', orange_box)
        worksheet.write('F31', '', light_green_box)
        worksheet.write('F32', '', yellow_box)
        worksheet.merge_range('G29:H29', "غیاب", arabic_format)
        worksheet.merge_range('G30:H30', "اجازتھ موظف", arabic_format)
        worksheet.merge_range('G31:H31', "اجازتہ رسمیتہ", arabic_format)
        worksheet.merge_range('G32:H32', "تم تعدیلہ یدویا بعد الا عتماد ", arabic_format)

        workbook.close()
        fp.seek(0)
        file_content = fp.read()
        fp.close()

        self.report_file = base64.b64encode(file_content)
        self.report_name = file_name
        self.is_printed = True

        if self.env.context.get('skip_attendance_report_action'):
            return True

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Report generated successfully!',
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_url',
                    'url': '/web/content/?model=%s&id=%s&field=report_file&filename_field=report_name&download=true' % (
                        self._name, self.id),
                    'target': 'self',
                }
            }
        }
