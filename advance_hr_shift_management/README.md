# Shift Management for Odoo 18

**Version:** 18.0.1.7.0  
**Category:** Human Resources  
**License:** OPL-1

A complete shift scheduling application for Odoo 18. Define shift templates, assign employees,
manage change requests through an approval workflow, and integrate with Attendance, Time Off,
and Payroll Work Entries.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Module Structure](#module-structure)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [User Guide](#user-guide)
7. [Approval Workflow & Emails](#approval-workflow--emails)
8. [Payroll Integration](#payroll-integration)
9. [Security Groups](#security-groups)
10. [Screenshots](#screenshots)

---

## Overview

Shift Management is a **standalone Odoo app** (not buried under Employees). It appears on the
Odoo home screen with its own icon and menu:

```
Shift Management
├── Dashboard
├── Shifts
├── Assignments
├── Change Requests
└── Regenerate Work Entries
```

The module is designed for companies running **multiple shifts** — morning, evening, night,
and overnight rotations that cross midnight (e.g. 18:00 – 02:00 +1 day).

---

## Features

| Area | What it does |
|------|--------------|
| **Shift Templates** | Define start/end hours, break, working days, color, work entry type. Midnight-cross support. |
| **Shift Assignments** | Link employees to shifts for date ranges. Draft → Active → Expired lifecycle. Overlap protection. |
| **Change Requests** | Manager-initiated shift changes with Draft → Submitted → Approved/Rejected/Cancelled workflow. |
| **Dashboard** | KPI cards, charts, today's roster, pending approvals, quick actions (OWL client action). |
| **Email Notifications** | Professional templates on submit, approve, reject, and cancel. |
| **Activities** | Planned activity assigned to approver on submit. |
| **Attendance** | Shows assigned shift, detects late arrivals with configurable grace period. |
| **Time Off** | Leave duration calculated from assigned shift hours per day. |
| **Work Entries** | Contract can use "Shift Assignments" as work entry source for planned payroll entries. |
| **Multi-company** | Shift templates scoped per company. Record rules for team-based access. |

---

## Module Structure

```
advance_hr_shift_management/
├── __manifest__.py
├── README.md
├── models/
│   ├── hr_shift_template.py       # Shift definitions
│   ├── hr_shift_assignment.py     # Employee ↔ shift scheduling
│   ├── hr_shift_change_request.py # Approval workflow + emails
│   ├── shift_dashboard.py         # Dashboard data API
│   ├── hr_contract.py             # work_entry_source = 'shift'
│   ├── hr_employee.py             # Shift intervals for leaves
│   ├── hr_attendance.py           # Late detection
│   ├── hr_leave.py                # Shift-aware leave duration
│   ├── hr_work_entry.py           # shift_assignment_id field
│   ├── res_company.py             # Default approver, grace period
│   └── res_config_settings.py
├── views/                         # Form, list, kanban, calendar views
├── wizard/
│   └── shift_work_entry_regenerate.py
├── data/
│   ├── ir_sequence_data.xml
│   ├── mail_activity_type_data.xml
│   └── mail_template_data.xml
├── security/
│   ├── hr_shift_security.xml      # Groups + record rules
│   └── ir.model.access.csv
├── static/
│   ├── description/               # Module info page (Apps → Module Info)
│   │   ├── index.html
│   │   ├── icon.png
│   │   └── screenshot_*.png
│   └── src/dashboard/             # OWL dashboard components
└── tests/
    └── test_shift_management.py
```

### Data Models

| Technical Name | Description |
|----------------|-------------|
| `hr.shift.template` | Company shift definition (times, break, working days) |
| `hr.shift.assignment` | Employee shift for a date range |
| `hr.shift.change.request` | Approval workflow record (SCR/00001 sequence) |

---

## Installation

1. Add `E_custom_addons` (or your custom addons path) to `addons_path` in `odoo.conf`.
2. Update the Apps list: **Apps → Update Apps List**.
3. Search **Shift Management** and click **Install**.
4. Assign security groups to users (see [Security Groups](#security-groups)).
5. Configure settings (see [Configuration](#configuration)).

### Upgrade

```bash
./odoo-bin -c odoo.conf -d YOUR_DB -u advance_hr_shift_management --stop-after-init
```

---

## Configuration

Go to **Settings → Employees** and scroll to the **Shift Management** block.

| Setting | Purpose |
|---------|---------|
| **Default Shift Approver** | Auto-filled on new change requests. Receives submit emails and activities. |
| **Grace Period (minutes)** | Tolerance before attendance is marked as late (default: 15 min). |

### Outgoing Mail Server

Email notifications require a configured outgoing mail server:

**Settings → Technical → Email → Outgoing Mail Servers**

Ensure approver users have a contact profile with a valid email address.

### Contract Work Entry Source (Payroll)

On each employee contract (**Employees → Contracts → Work Entries** tab):

- **Shift Assignments** — planned work entries from the shift schedule
- **Attendances** — pay based on actual check-in/check-out (hourly wage)

---

## User Guide

### 1. Create Shift Templates

**Shift Management → Shifts → New**

| Field | Example |
|-------|---------|
| Name | Morning Shift |
| Start Hour | 8.0 (08:00) |
| End Hour | 17.0 (17:00) |
| Break | 15 minutes |
| Crosses Midnight | No |
| Working Days | Mon–Fri |

For night shifts: Start 18.0, End 2.0, enable **Crosses Midnight**.

### 2. Assign Shifts to Employees

**Shift Management → Assignments → New**

- Select employee and shift template
- Set **Date From** and **Date To**
- Click **Activate** to make the assignment active

Overlapping active assignments for the same employee are blocked.

### 3. Submit a Change Request

**Shift Management → Change Requests → New**

1. Select employee and requested shift
2. Set effective dates and reason
3. Confirm approver (defaults from company settings)
4. Click **Submit**

The approver receives an email and a planned activity.

### 4. Approve or Reject

Open the submitted request. The approver clicks:

- **Approve** — creates a new active assignment, notifies requester and employee
- **Reject** — fill rejection reason (optional), notifies requester and employee
- **Cancel** — available to requester while in submitted state

### 5. Monitor from Dashboard

**Shift Management → Dashboard**

View KPIs, charts, today's roster, pending approvals, and use quick action buttons.

### 6. Regenerate Work Entries (Officer only)

After schedule changes when using **Shift Assignments** work entry source:

**Shift Management → Regenerate Work Entries**

Select date range and employees to rebuild planned work entries.

---

## Approval Workflow & Emails

```
Draft ──Submit──► Submitted ──Approve──► Approved (assignment created)
                     │
                     ├──Reject──► Rejected
                     └──Cancel──► Cancelled
```

| Action | Email Template | Recipients |
|--------|---------------|------------|
| Submit | Shift Management: Approval Required | Approver |
| Approve | Shift Management: Request Approved | Requester + Employee |
| Reject | Shift Management: Request Rejected | Requester + Employee |
| Cancel | Shift Management: Request Cancelled | Requester + Approver |

Emails are logged in the record chatter. If mail server is not configured, the request still
processes and a warning is posted in chatter.

---

## Payroll Integration

### Mode A — Planned Schedule (Shift Assignments)

Best for fixed monthly salary based on scheduled hours.

1. Contract → Work Entry Source = **Shift Assignments**
2. Create shift assignments for the period
3. Run **Regenerate Work Entries** after changes
4. Compute payslip as usual

### Mode B — Actual Hours (Attendances)

Best for hourly pay based on real attendance.

1. Contract → Work Entry Source = **Attendances**
2. Set hourly wage on contract
3. Shift Management still handles scheduling, late marks, and approvals
4. No daily work entry regeneration needed

---

## Security Groups

Configure under **Settings → Users → [User] → Shift Management**:

| Group | Permissions |
|-------|-------------|
| **User** | Dashboard, own change requests |
| **Manager** | + Create assignments, submit requests for team |
| **Approver** | + Approve/reject assigned requests |
| **Officer** | + Shift templates, all records, regenerate work entries |

Record rules ensure managers see only their team; officers see all.

---

## Screenshots

Screenshots are included in `static/description/` and displayed in the Odoo **Module Info** page:

| File | Content |
|------|---------|
| `screenshot_dashboard.png` | Executive dashboard with KPIs and roster |
| `screenshot_shifts.png` | Shift template list |
| `screenshot_assignments.png` | Employee shift assignments |
| `screenshot_change_requests.png` | Change requests kanban |
| `screenshot_approval_email.png` | Email notification in chatter |
| `screenshot_change_request_form.png` | Request form with approve/reject |

View in Odoo: **Apps → Shift Management → Module Info** (or click the module card info icon).

---

## Testing

```bash
./odoo-bin -c odoo.conf -d YOUR_DB --test-enable --stop-after-init \
  -u advance_hr_shift_management --test-tags advance_hr_shift_management
```

8 automated tests cover night shifts, overlap constraints, approval workflow, work entries,
late detection, leave duration, and monthly rotation.

---

## Support

For implementation support, contact your Odoo partner or refer to this README and the
in-app module description page.
