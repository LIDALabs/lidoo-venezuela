import base64
import io
import json
import logging
import urllib.request
from urllib.parse import urlencode

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LidooAnalyticsTicket(models.Model):
    _name = "lidoo.analytics.ticket"
    _description = "Ticket de analítica"
    _order = "create_date desc"

    description = fields.Text(string="Descripción", required=True)
    screenshot = fields.Binary(string="Captura de pantalla")
    screenshot_filename = fields.Char(string="Nombre de archivo")
    has_screenshot = fields.Boolean(
        string="Tiene captura",
        compute="_compute_has_screenshot",
        store=True,
    )
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
    db_name = fields.Char(string="Base de Datos/Empresa", readonly=True)

    @api.depends("screenshot")
    def _compute_has_screenshot(self):
        for ticket in self:
            ticket.has_screenshot = bool(ticket.screenshot)

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
                    files[filename] = image_bytes
                    # Reference the attached file so Discord renders it inline
                    payload["embeds"][0]["image"] = {"url": f"attachment://{filename}"}
                    _logger.info(
                        "Ticket %s screenshot ready: %s (%d bytes)",
                        self.id,
                        filename,
                        len(image_bytes),
                    )
                except Exception:
                    _logger.warning("Could not decode screenshot for ticket %s", self.id, exc_info=True)

            payload_json = json.dumps(payload, default=str)
            _logger.info(
                "Ticket %s sending to Discord: payload_json=%s, files=%s",
                self.id,
                payload_json,
                list(files.keys()) or "none",
            )

            # Build multipart request manually using urllib
            boundary = "----OdooBoundary"
            body = []

            # Add payload_json field
            body.append(f"--{boundary}")
            body.append('Content-Disposition: form-data; name="payload_json"')
            body.append("")
            body.append(payload_json)

            # Add file if exists
            if files:
                for fname, fcontent in files.items():
                    body.append(f"--{boundary}")
                    body.append(f'Content-Disposition: form-data; name="file"; filename="{fname}"')
                    body.append("Content-Type: image/png")
                    body.append("")
                    body.append(fcontent.decode("latin1") if isinstance(fcontent, bytes) else fcontent)

            body.append(f"--{boundary}--")
            body.append("")

            data = "\r\n".join(body).encode("utf-8")
            if files:
                # If we have binary content, we need to handle it differently
                # Rebuild with proper binary handling
                body_lines = []
                body_lines.append(f"--{boundary}".encode())
                body_lines.append(b'Content-Disposition: form-data; name="payload_json"')
                body_lines.append(b"")
                body_lines.append(payload_json.encode())

                for fname, fcontent in files.items():
                    body_lines.append(f"--{boundary}".encode())
                    body_lines.append(f'Content-Disposition: form-data; name="file"; filename="{fname}"'.encode())
                    body_lines.append(b"Content-Type: image/png")
                    body_lines.append(b"")
                    body_lines.append(fcontent if isinstance(fcontent, bytes) else fcontent.encode())

                body_lines.append(f"--{boundary}--".encode())
                body_lines.append(b"")
                data = b"\r\n".join(body_lines)

            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_body = resp.read().decode("utf-8")[:500]
                status_code = resp.status
                _logger.info(
                    "Ticket %s Discord response: HTTP %s, body=%s",
                    self.id,
                    status_code,
                    resp_body,
                )

                if status_code >= 200 and status_code < 300:
                    _logger.info("Ticket %s sent to Discord (HTTP %s)", self.id, status_code)
                    self.write({"state": "sent", "error_message": False})
                else:
                    _logger.warning(
                        "Ticket %s failed: HTTP %s %s",
                        self.id,
                        status_code,
                        resp_body[:200],
                    )
                    self.write({
                        "state": "failed",
                        "error_message": f"HTTP {status_code}: {resp_body[:500]}",
                    })

        except urllib.error.HTTPError as e:
            resp_body = e.read().decode("utf-8")[:500]
            _logger.warning(
                "Ticket %s Discord HTTP error: %s, body=%s",
                self.id,
                e.code,
                resp_body,
                exc_info=True,
            )
            self.write({"state": "failed", "error_message": f"HTTP {e.code}: {resp_body[:256]}"})
        except urllib.error.URLError as e:
            _logger.warning("Request error sending ticket %s: %s", self.id, e, exc_info=True)
            self.write({"state": "failed", "error_message": str(e)[:256]})
        except Exception as e:
            _logger.error("Unexpected error sending ticket %s: %s", self.id, e, exc_info=True)
            self.write({"state": "failed", "error_message": f"Unexpected: {e}"[:256]})

    def _build_discord_embed(self):
        """Build a Discord embed dict from the ticket record fields.

        The embed is combined with an attached screenshot file (if available)
        when action_send() POSTs via multipart. Field values are truncated to
        stay within Discord's embed limits.
        """
        reporter = self.user_id.name or self.user_id.login or "Desconocido"
        db_info = self.db_name or "Desconocida"
        embed = {
            "title": f"Incidencia #{self.id}"[:256],
            "description": (self.description or "Sin descripción")[:4096],
            "color": 15105570,  # LIDA brand purple
            "fields": [
                {
                    "name": "Usuario",
                    "value": reporter[:1024],
                    "inline": True,
                },
                {
                    "name": "Base de Datos/Empresa",
                    "value": db_info[:1024],
                    "inline": True,
                },
            ],
            "footer": {
                "text": f"Reportado por {reporter} | DB: {db_info}"[:2048],
            },
        }

        if self.create_date:
            embed["timestamp"] = str(self.create_date)

        # Route
        if self.current_route:
            embed["fields"].append({
                "name": "Ruta",
                "value": self.current_route[:1024],
                "inline": True,
            })

        # Screenshot indicator
        if self.screenshot:
            filename = self.screenshot_filename or "attachment"
            embed["fields"].append({
                "name": "Captura",
                "value": f"{filename[:1000]} — incluida abajo",
                "inline": True,
            })

        # Server logs
        if self.server_logs:
            logs = self.server_logs[:1000]
            embed["fields"].append({
                "name": "Logs del servidor",
                "value": f"```\n{logs}\n```",
            })

        return embed


