/** @odoo-module **/
import { Component, useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { openTicketWizard } from "./ticket_utils";

export class TicketSystray extends Component {
    static template = "lidoo_analytics_client.TicketSystray";

    setup() {
        this.actionService = useService("action");
        this._onKeyDown = this._onKeyDown.bind(this);
        useEffect(() => {
            document.addEventListener("keydown", this._onKeyDown);
            return () => document.removeEventListener("keydown", this._onKeyDown);
        }, () => []);
    }

    _onKeyDown(ev) {
        // Ctrl+Shift+E abre el wizard de incidencia desde cualquier pantalla,
        // incluso cuando hay un modal abierto.
        if (ev.ctrlKey && ev.shiftKey && (ev.key === "e" || ev.key === "E")) {
            ev.preventDefault();
            this.openTicket();
        }
    }

    async openTicket() {
        await openTicketWizard(this.actionService);
    }
}

registry.category("systray").add("lidoo_analytics_client.TicketSystray", {
    Component: TicketSystray,
});
