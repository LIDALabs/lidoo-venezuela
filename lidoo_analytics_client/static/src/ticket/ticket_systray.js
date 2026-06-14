/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class TicketSystray extends Component {
    static template = "lidoo_analytics_client.TicketSystray";

    setup() {
        this.dialog = useService("dialog");
    }

    openTicket() {
        this.dialog.add(TicketDialog);
    }
}

export class TicketDialog extends Component {
    static template = "lidoo_analytics_client.TicketDialog";
    static props = { close: Function };
}

registry.category("systray").add("lidoo_analytics_client.TicketSystray", {
    Component: TicketSystray,
});
