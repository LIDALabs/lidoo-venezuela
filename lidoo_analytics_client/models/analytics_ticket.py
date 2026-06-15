import json
import logging
import urllib.request
import urllib.error

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LidooAnalyticsTicket(models.Model):
    _name = "lidoo.analytics.ticket"
    _description = "Analytics Ticket"
    _order = "create_date desc"

    description = fields.Text(string="Description", required=True)
    screenshot = fields.Binary(string="Screenshot")
    screenshot_filename = fields.Char(string="Screenshot filename")
    current_route = fields.Char(string="Current Route")
    server_logs = fields.Text(string="Server Logs")
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("failed", "Failed"),
        ],
        string="Status",
        default="draft",
        readonly=True,
    )
    error_message = fields.Text(string="Error Message", readonly=True)
    user_id = fields.Many2one(
        "res.users", string="User", default=lambda self: self.env.user, readonly=True
    )

    def action_send(self):
        """Send this ticket to the configured webhook endpoint."""
        self.ensure_one()

        payload = self._build_payload()
        icp = self.env["ir.config_parameter"].sudo()
        webhook_url = icp.get_param("lidoo_analytics_ticket.webhook_url", "")

        # Siempre escribir payload de prueba para debug
        self._dump_payload(payload)

        if not webhook_url:
            _logger.info("No webhook configured, ticket %s saved as draft", self.id)
            self.write({"state": "draft"})
            return

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                _logger.info(
                    "Ticket %s sent to webhook, response: %s %s",
                    self.id,
                    resp.status,
                    resp.read()[:200],
                )
            self.write({"state": "sent"})
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            _logger.warning("Failed to send ticket %s: %s", self.id, e)
            self.write(
                {"state": "failed", "error_message": str(e)[:256]}
            )
        except Exception as e:
            _logger.error("Unexpected error sending ticket %s: %s", self.id, e)
            self.write(
                {"state": "failed", "error_message": f"Unexpected: {e}"[:256]}
            )

    def _build_payload(self):
        screenshot = self.screenshot or ""
        if isinstance(screenshot, bytes):
            screenshot = screenshot.decode("utf-8")
        _logger.info(
            "Building payload for ticket %s: screenshot=%d chars",
            self.id,
            len(screenshot),
        )
        return {
            "id": self.id,
            "description": self.description,
            "current_route": self.current_route,
            "server_logs": self.server_logs[:5000] if self.server_logs else "",
            "screenshot": screenshot,
            "screenshot_filename": self.screenshot_filename or "",
            "user_id": self.user_id.id if self.user_id else None,
            "user_login": self.user_id.login if self.user_id else "",
            "create_date": str(self.create_date) if self.create_date else "",
        }

    def _dump_payload(self, payload):
        """Write payload to a debug file for testing."""
        import os
        log_dir = "/etc/odoo/tickets"
        try:
            os.makedirs(log_dir, exist_ok=True)
            path = os.path.join(log_dir, f"ticket_{self.id}.json")
            with open(path, "w") as f:
                json.dump(payload, f, indent=2)
            _logger.info("Payload dumped to %s", path)
        except Exception as e:
            _logger.warning("Could not dump payload: %s", e)
