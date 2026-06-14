/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { TicketDialog } from "./ticket_dialog";

export class TicketSystray extends Component {
    static template = "lidoo_analytics_client.TicketSystray";

    setup() {
        this.dialog = useService("dialog");
    }

    openTicket() {
        this.dialog.add(TicketDialog);
    }
}

registry.category("systray").add("lidoo_analytics_client.TicketSystray", {
    Component: TicketSystray,
});
