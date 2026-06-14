/** @odoo-module **/
import { Component, useState, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class TicketDialog extends Component {
    static template = "lidoo_analytics_client.TicketDialog";
    static props = {
        close: { type: Function },
    };

    setup() {
        this.state = useState({
            userText: "",
            currentRoute: "",
            currentView: "",
            isLoading: true,
            submitting: false,
        });

        this.router = useService("router");
        this.action = useService("action");

        onMounted(() => {
            this._captureContext();
        });
    }

    _captureContext() {
        try {
            const hash = this.router.current?.hash;
            this.state.currentRoute = hash ? JSON.stringify(hash) : "N/A";

            const controller = this.action.currentController;
            if (controller && controller.title) {
                this.state.currentView = controller.title;
            }
        } catch (_e) {
            this.state.currentRoute = "N/A";
            this.state.currentView = "Unknown";
        } finally {
            this.state.isLoading = false;
        }
    }

    close() {
        this.props.close();
    }
}
