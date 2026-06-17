import base64
import io
import json
import logging

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LidooAnalyticsTicket(models.Model):
    _name = "lidoo.analytics.ticket"
    _description = "Ticket de analítica"
    _order = "create_date desc"

    description = fields.Text(string="Descripción", required=True)
    screenshot = fields.Binary(string="Captura de pantalla")
    screenshot_filename = fields.Char(string="Nombre de archivo")
    current_route = fields.Char(string="Ruta actual")
    server_logs = fields.Text(string="Registros del servidor")
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("sent", "Enviado"),
            ("failed", "Fallido"),
        ],
        string="Estado",
        default="draft",
        readonly=True,
    )
    error_message = fields.Text(string="Mensaje de error", readonly=True)
    user_id = fields.Many2one(
        "res.users", string="Usuario", default=lambda self: self.env.user, readonly=True
    )

    def action_send(self):
        """Send this ticket to the configured Discord webhook.

        Uses multipart/form-data to attach the screenshot as an image file
        so Discord can display it inline in the embed.
        """
        self.ensure_one()

        icp = self.env["ir.config_parameter"].sudo()
        webhook_url = icp.get_param("lidoo_analytics_ticket.webhook_url", "")

        if not webhook_url:
            _logger.info("No webhook configured, ticket %s saved as draft", self.id)
            self.write({"state": "draft"})
            return

        try:
            embed = self._build_discord_embed()
            payload = {"embeds": [embed]}
            files = {}

            # Decode the screenshot binary and attach it as a file
            raw = self.screenshot or ""
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            if raw:
                try:
                    image_bytes = base64.b64decode(raw)
                    filename = self.screenshot_filename or f"ticket_{self.id}.png"
                    files["file[0]"] = (filename, io.BytesIO(image_bytes), "image/png")
                    # Reference the attached file so Discord renders it inline
                    payload["embeds"][0]["image"] = {"url": f"attachment://{filename}"}
                except Exception:
                    _logger.warning("Could not decode screenshot for ticket %s", self.id, exc_info=True)

            resp = requests.post(
                webhook_url,
                data={"payload_json": json.dumps(payload)},
                files=files,
                timeout=30,
            )

            if resp.ok:
                _logger.info("Ticket %s sent to Discord (HTTP %s)", self.id, resp.status_code)
                self.write({"state": "sent"})
            else:
                _logger.warning(
                    "Ticket %s failed: HTTP %s %s",
                    self.id,
                    resp.status_code,
                    resp.text[:200],
                )
                self.write({
                    "state": "failed",
                    "error_message": f"HTTP {resp.status_code}",
                })

        except requests.RequestException as e:
            _logger.warning("Request error sending ticket %s: %s", self.id, e)
            self.write({"state": "failed", "error_message": str(e)[:256]})
        except Exception as e:
            _logger.error("Unexpected error sending ticket %s: %s", self.id, e)
            self.write({"state": "failed", "error_message": f"Unexpected: {e}"[:256]})

    def _build_discord_embed(self):
        """Build a Discord embed dict from the ticket record fields.

        The embed is combined with an attached screenshot file (if available)
        when action_send() POSTs via multipart.
        """
        embed = {
            "title": f"Incidencia #{self.id}",
            "description": self.description or "Sin descripción",
            "color": 15105570,  # LIDA brand purple
            "fields": [],
            "footer": {
                "text": f"Reportado por {self.user_id.login if self.user_id else 'Desconocido'}",
            },
        }

        if self.create_date:
            embed["timestamp"] = str(self.create_date)

        # Route
        if self.current_route:
            route = self.current_route
            embed["fields"].append({
                "name": "Ruta",
                "value": route[:250],
                "inline": True,
            })

        # Screenshot indicator
        if self.screenshot:
            filename = self.screenshot_filename or "attachment"
            embed["fields"].append({
                "name": "Captura",
                "value": f"{filename} — incluida abajo",
                "inline": True,
            })

        # Server logs
        if self.server_logs:
            logs = self.server_logs[:1500]
            embed["fields"].append({
                "name": "Logs del servidor",
                "value": f"```\n{logs}\n```",
            })

        return embed


