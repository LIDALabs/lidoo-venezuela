from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestAnalyticsTicketDelivery(TransactionCase):

    def test_clickup_delivery_is_not_reset_when_discord_is_unconfigured(self):
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("lidoo_analytics.clickup_api_token", "clickup-token")
        icp.set_param("lidoo_analytics.clickup_list_id", "clickup-list")
        icp.set_param("lidoo_analytics_ticket.webhook_url", "")
        ticket = self.env["lidoo.analytics.ticket"].create(
            {"description": "No puedo confirmar", "screenshot": "c2NyZWVuc2hvdA=="}
        )

        with patch(
            "odoo.addons.lidoo_analytics_client.models.analytics_ticket.LidooAnalyticsTicket._clickup_create_task",
            return_value="task-123",
        ), patch(
            "odoo.addons.lidoo_analytics_client.models.analytics_ticket.LidooAnalyticsTicket._clickup_upload_attachment"
        ):
            ticket.action_send_clickup()
            ticket.action_send()

        self.assertEqual(ticket.clickup_task_id, "task-123")
        self.assertEqual(ticket.state, "sent")
