/** @odoo-module **/
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { openTicketWizard } from "./ticket_utils";

export class LidooFloatingTicketButton extends Component {
    static template = "lidoo_analytics_client.LidooFloatingTicketButton";

    setup() {
        this.actionService = useService("action");
        this.state = useState({ modalOpen: false });
        this._observer = null;

        onMounted(() => {
            this._observer = new MutationObserver(() => this._checkModal());
            this._observer.observe(document.body, { childList: true, subtree: true });
            this._checkModal();
        });

        onWillUnmount(() => {
            if (this._observer) {
                this._observer.disconnect();
            }
        });
    }

    _checkModal() {
        // Bootstrap/Odoo modals and OWL dialogs
        const modalOpen = Boolean(
            document.querySelector(".modal.show, .modal[style*='display: block'], .o_dialog")
        );
        this.state.modalOpen = modalOpen;
    }

    async onClick() {
        await openTicketWizard(this.actionService);
    }
}

registry.category("main_components").add("lidoo_analytics_client.LidooFloatingTicketButton", {
    Component: LidooFloatingTicketButton,
});
