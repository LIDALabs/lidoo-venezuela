/** @odoo-module **/
import { Component, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class AnalyticsSystray extends Component {
    static template = "lidoo_analytics_client.AnalyticsSystray";

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.lastStatus = { status: "none" };

        onWillStart(async () => {
            await this._loadLastStatus();
        });
    }

    async _loadLastStatus() {
        try {
            const logs = await this.orm.searchRead(
                "lidoo.analytics.log",
                [],
                ["status", "send_date"],
                { limit: 1, order: "send_date desc" },
            );
            this.lastStatus = logs.length ? logs[0] : { status: "none" };
        } catch {
            this.lastStatus = { status: "none" };
        }
    }

    onClick() {
        this.action.doAction("lidoo_analytics_client.action_lidoo_analytics_log");
    }

    get statusIcon() {
        switch (this.lastStatus.status) {
            case "success":
                return "fa-check-circle text-success";
            case "error":
                return "fa-exclamation-triangle text-danger";
            default:
                return "fa-bar-chart text-muted";
        }
    }

    get statusTitle() {
        switch (this.lastStatus.status) {
            case "success":
                return _t("Last report: OK");
            case "error":
                return _t("Last report: Failed");
            default:
                return _t("Analytics");
        }
    }
}

registry.category("systray").add("lidoo_analytics_client.AnalyticsSystray", {
    Component: AnalyticsSystray,
});
