# -*- coding: utf-8 -*-
from calendar import monthrange
from datetime import datetime, timedelta
import base64
import io

import xlsxwriter

from odoo import fields, models


class DepartmentAttendanceReportWizard(models.TransientModel):
    _name = "department.attendance.report.wizard"
    _description = "All employees / Dept attendance report (XLSX)"

    department_id = fields.Many2one(
        "hr.department",
        string="Department",
        help="Optional. Leave empty to include all employees (subject to your access rights). "
        "If set, only employees in this department are included.",
    )
    include_child_departments = fields.Boolean(
        string="Include Sub-departments",
        default=True,
    )
    month = fields.Selection(
        [
            ("January", "January"),
            ("February", "February"),
            ("March", "March"),
            ("April", "April"),
            ("May", "May"),
            ("June", "June"),
            ("July", "July"),
            ("August", "August"),
            ("September", "September"),
            ("October", "October"),
            ("November", "November"),
            ("December", "December"),
        ],
        string="Month",
        required=True,
        default=lambda self: datetime.now().strftime("%B"),
    )
    year = fields.Integer(
        string="Year",
        required=True,
        default=lambda self: int(datetime.now().strftime("%Y")),
    )
    report_header = fields.Char(string="Report Header", required=True, default="PMMS")

    report_file = fields.Binary("File", readonly=True)
    report_name = fields.Char("File Name", readonly=True)

    def _month_date_range(self):
        self.ensure_one()
        month_index = list(dict(self._fields["month"].selection).keys()).index(self.month) + 1
        date_from = datetime(self.year, month_index, 1)
        last_day = monthrange(self.year, month_index)[1]
        date_to = datetime(self.year, month_index, last_day)
        return date_from, date_to

    def _employees_for_department(self):
        self.ensure_one()
        if not self.department_id:
            return self.env["hr.employee"].search([], order="id asc")
        domain = [
            (
                "department_id",
                "child_of" if self.include_child_departments else "=",
                self.department_id.id,
            )
        ]
        return self.env["hr.employee"].search(domain, order="id asc")

    def export_department_attendance_xlsx(self):
        self.ensure_one()
        date_from, date_to = self._month_date_range()

        dept_label = (
            self.department_id.display_name.replace("/", "-")
            if self.department_id
            else "All_Employees"
        )
        file_name = (
            f"Attendance_{dept_label}_{self.year}_{self.month}_"
            f"{date_from.strftime('%Y-%m-%d')}_to_{date_to.strftime('%Y-%m-%d')}.xlsx"
        )

        fp = io.BytesIO()
        workbook = xlsxwriter.Workbook(fp, {"in_memory": True})
        worksheet = workbook.add_worksheet("Report")

        header_format = workbook.add_format(
            {
                "bold": True,
                "font_color": "black",
                "bg_color": "#ADD8E6",
                "align": "center",
                "valign": "vcenter",
                "border": 2,
                "text_wrap": True,
            }
        )
        data_format = workbook.add_format(
            {"align": "center", "valign": "vcenter", "border": 1, "text_wrap": True}
        )
        inout_total_format = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "border": 2,
                "bg_color": "#D3EAFD",
                "text_wrap": True,
            }
        )

        # Header rows
        worksheet.set_row(0, 40)
        worksheet.set_row(1, 30)
        worksheet.merge_range("A1:D1", self.report_header or "PMMS", header_format)
        worksheet.merge_range("E1:G1", f"YEAR\n{self.year}", header_format)
        worksheet.merge_range("H1:J1", f"MONTH\n{self.month}", header_format)

        num_days = (date_to - date_from).days + 1
        start_header_col = 10
        end_header_col = start_header_col + num_days - 6
        worksheet.merge_range(
            0,
            start_header_col,
            0,
            end_header_col,
            "MONTH ATTENDANCE SHEET",
            header_format,
        )

        worksheet.write("A2", "ID", header_format)
        worksheet.write("B2", "Name", header_format)
        worksheet.merge_range("C2:D2", "IN/OUT/TOTAL", header_format)

        # Date headers
        start_col = 4
        current_col = start_col
        current_date = date_from
        date_columns = []
        while current_date <= date_to:
            day_text = f"{current_date.strftime('%a')}\n{current_date.strftime('%Y-%m-%d')}"
            worksheet.write(1, current_col, day_text, data_format)
            worksheet.set_column(current_col, current_col, 12)
            date_columns.append((current_date.date(), current_col))
            current_col += 1
            current_date += timedelta(days=1)

        worksheet.set_column(0, 0, 10)
        worksheet.set_column(1, 1, 25)
        worksheet.set_column(2, 3, 12)

        employees = self._employees_for_department()
        Log = self.env["hik.attendance.log"]

        row = 2
        for emp in employees:
            logs = Log.search(
                [
                    ("employee_id", "=", emp.id),
                    ("attendance_date", ">=", date_from.date()),
                    ("attendance_date", "<=", date_to.date()),
                ],
                order="attendance_date asc, event_time asc",
            )

            daily_punches = {}
            for log in logs:
                dt_in = fields.Datetime.context_timestamp(self, log.event_time)
                dt_out = (
                    fields.Datetime.context_timestamp(self, log.last_event_time)
                    if log.last_event_time
                    else None
                )
                d = dt_in.date()
                punches = [dt_in]
                if dt_out:
                    punches.append(dt_out)
                daily_punches.setdefault(d, []).extend(punches)

            # Employee identifier: prefer employee_no (badge), else internal ID
            emp_id = getattr(emp, "employee_no", False) or emp.id
            emp_id_text = str(emp_id)

            worksheet.set_row(row, 20)
            worksheet.set_row(row + 1, 20)
            worksheet.set_row(row + 2, 20)

            worksheet.merge_range(row, 0, row + 2, 0, emp_id_text, data_format)
            worksheet.merge_range(row, 1, row + 2, 1, emp.name or "", data_format)
            worksheet.merge_range(row, 2, row, 3, "In", inout_total_format)
            worksheet.merge_range(row + 1, 2, row + 1, 3, "Out", inout_total_format)
            worksheet.merge_range(row + 2, 2, row + 2, 3, "Total", inout_total_format)

            for log_date, col in date_columns:
                punches = daily_punches.get(log_date, [])
                punches = sorted(punches)
                has_checkout = len(punches) >= 2 and punches[-1] != punches[0]
                in_time = punches[0].strftime("%H:%M") if punches else ""
                out_time = punches[-1].strftime("%H:%M") if has_checkout else "00"
                total_hours = ""
                if has_checkout:
                    try:
                        in_dt = punches[0]
                        out_dt = punches[-1]
                        if out_dt < in_dt:
                            out_dt += timedelta(days=1)
                        total_hours = str(out_dt - in_dt).split(".")[0]
                    except Exception:
                        total_hours = ""

                worksheet.write(row, col, in_time, data_format)
                worksheet.write(row + 1, col, out_time, data_format)
                worksheet.write(row + 2, col, total_hours, data_format)

            row += 3

        workbook.close()
        fp.seek(0)
        self.report_file = base64.b64encode(fp.read())
        self.report_name = file_name

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/?model=%s&id=%s&field=report_file&filename_field=report_name&download=true"
            % (self._name, self.id),
            "target": "self",
        }

