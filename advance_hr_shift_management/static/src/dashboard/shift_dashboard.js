/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

const DONUT_COLORS = ["#22c55e", "#f97316", "#6366f1", "#3b82f6", "#ef4444", "#ec4899"];

export class ShiftManagementDashboard extends Component {
    static template = "advance_hr_shift_management.ShiftDashboard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            loading: true,
            data: null,
            animated: {},
            refreshing: false,
        });
        onWillStart(() => this.loadDashboard());
    }

    async loadDashboard() {
        this.state.refreshing = !this.state.loading;
        if (!this.state.refreshing) {
            this.state.loading = true;
        }
        const data = await this.orm.call("hr.shift.assignment", "get_dashboard_data", []);
        this.state.data = data;
        this.state.loading = false;
        this.state.refreshing = false;
        this._animateCounters(data?.kpis || {});
    }

    _animateCounters(kpis) {
        const keys = [
            "month_total", "approved_count", "on_shift_today",
            "present_today", "pending_approvals", "approval_rate",
        ];
        const targets = {};
        for (const k of keys) {
            targets[k] = kpis[k] || 0;
            this.state.animated[k] = 0;
        }
        const duration = 900;
        const start = performance.now();
        const step = (now) => {
            const t = Math.min((now - start) / duration, 1);
            const ease = 1 - Math.pow(1 - t, 3);
            for (const k of keys) {
                this.state.animated[k] = Math.round(targets[k] * ease);
            }
            if (t < 1) {
                requestAnimationFrame(step);
            }
        };
        requestAnimationFrame(step);
    }

    display(key) {
        return this.state.animated[key] ?? 0;
    }

    get kpis() {
        return this.state.data?.kpis || {};
    }

    get roster() {
        return this.state.data?.roster || [];
    }

    get pendingApprovals() {
        return this.state.data?.pending_approvals || [];
    }

    get shiftDistribution() {
        return this.state.data?.shift_distribution || [];
    }

    get monthlyChart() {
        return this.state.data?.monthly_chart || [];
    }

    get donutStyle() {
        const dist = this.shiftDistribution;
        if (!dist.length) {
            return "background: conic-gradient(#e5e7eb 0% 100%);";
        }
        let acc = 0;
        const parts = dist.map((s) => {
            const start = acc;
            acc += s.percent;
            return `${s.color} ${start}% ${acc}%`;
        });
        return `background: conic-gradient(${parts.join(", ")});`;
    }

    get approvalLinePoints() {
        const rate = this.kpis.approval_rate || 0;
        const pts = [10, 55, 30, 40, 55, 28, 75, 18, 90, 35];
        const scale = rate / 100;
        return pts.map((y, i) => `${i * 10},${70 - (70 - y) * scale}`).join(" ");
    }

    growthClass() {
        return (this.kpis.growth_pct || 0) >= 0 ? "up" : "down";
    }

    getInitial(name) {
        if (!name) {
            return "?";
        }
        return name.trim().charAt(0).toUpperCase();
    }

    async openAction(xmlid, extraContext = {}) {
        const action = await this.orm.call(
            "hr.shift.assignment", "get_dashboard_action", [xmlid]
        );
        if (action) {
            action.context = { ...(action.context || {}), ...extraContext };
            this.actionService.doAction(action);
        }
    }

    openShifts() {
        return this.openAction("advance_hr_shift_management.hr_shift_template_action");
    }

    openAssignments() {
        return this.openAction("advance_hr_shift_management.hr_shift_assignment_action");
    }

    openChangeRequests() {
        return this.openAction("advance_hr_shift_management.hr_shift_change_request_action");
    }

    openPendingApprovals() {
        return this.openAction("advance_hr_shift_management.hr_shift_change_request_action", {
            search_default_submitted: 1,
        });
    }

    openNewAssignment() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Assign Shift"),
            res_model: "hr.shift.assignment",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openNewChangeRequest() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Shift Change Request"),
            res_model: "hr.shift.change.request",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openRequest(requestId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.shift.change.request",
            res_id: requestId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAssignment(assignmentId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.shift.assignment",
            res_id: assignmentId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAttendances() {
        return this.openAction("hr_attendance.hr_attendance_action");
    }
}

registry.category("actions").add("shift_management_dashboard", ShiftManagementDashboard);
