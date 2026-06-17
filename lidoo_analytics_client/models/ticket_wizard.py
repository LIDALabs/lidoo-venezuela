import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class LidooAnalyticsTicketWizard(models.TransientModel):
    _name = "lidoo.analytics.ticket.wizard"
    _description = "Asistente para reportar incidencias"

    description = fields.Text(string="Descripción", required=True)
    screenshot = fields.Binary(string="Captura de pantalla")
    screenshot_filename = fields.Char(string="Nombre de archivo")
    current_route = fields.Char(string="Ruta actual")
    server_logs = fields.Text(string="Registros del servidor")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        ctx = self.env.context
        if ctx.get("default_screenshot"):
            _logger.info(
                "Screenshot received in context: %d chars",
                len(ctx["default_screenshot"]),
            )
        else:
            _logger.warning("No screenshot in context")

        if "server_logs" in fields_list:
            res["server_logs"] = self._fetch_server_logs()

        return res

    @api.model_create_multi
    def create(self, vals_list):
        """
        CAPA DE DEFENSA ABSOLUTA:
        Interceptamos la creación del registro transient en la base de datos.
        Como el contexto del JS viene AQUÍ con total seguridad, forzamos la inyección
        del Base64 directamente en los valores antes de escribir el registro.
        """
        ctx = self.env.context
        _logger.info("--- WIZARD TRANSIENT CREATE TRIGGERED ---")

        for vals in vals_list:
            if not vals.get("screenshot") and ctx.get("default_screenshot"):
                vals["screenshot"] = ctx["default_screenshot"]
                _logger.info(
                    "SUCCESS: Screenshot injected into transient record (%d chars)",
                    len(vals["screenshot"]),
                )

            if not vals.get("screenshot_filename") and ctx.get(
                "default_screenshot_filename"
            ):
                vals["screenshot_filename"] = ctx["default_screenshot_filename"]

            if not vals.get("current_route") and ctx.get("default_current_route"):
                vals["current_route"] = ctx["default_current_route"]

        return super(LidooAnalyticsTicketWizard, self).create(vals_list)

    def write(self, vals):
        """
        BLOQUEO DE VACIADO:
        Cuando el frontend ejecuta 'web_save', si el campo 'screenshot' no estaba
        en la vista XML (por falta de upgrade), el JSON enviado por el JS incluirá
        un 'screenshot: False'. Este override bloquea que se borre el dato que
        ya rescatamos en el método create().
        """
        if "screenshot" in vals and not vals["screenshot"]:
            if self.screenshot:
                _logger.info(
                    "PROTECTION: Blocked frontend web_save from erasing the screenshot."
                )
                vals.pop("screenshot")

        return super(LidooAnalyticsTicketWizard, self).write(vals)

    def action_submit(self):
        self.ensure_one()

        if not self.description or not self.description.strip():
            raise UserError(
                _("Por favor, proporcione una descripción de la incidencia antes de enviar.")
            )

        _logger.info("--- ACTION SUBMIT PROCESSING ---")
        _logger.info(
            "Final transient record screenshot size: %d bytes",
            len(self.screenshot) if self.screenshot else 0,
        )

        # Crear el ticket persistente real con los datos blindados
        ticket = self.env["lidoo.analytics.ticket"].create(
            {
                "description": self.description.strip(),
                "screenshot": self.screenshot,
                "screenshot_filename": self.screenshot_filename or "screenshot.png",
                "current_route": self.current_route,
                "server_logs": self.server_logs,
            }
        )

        # Enviar automáticamente a Discord si hay webhook configurado
        ticket.action_send()

        return {"type": "ir.actions.act_window_close"}

    def _fetch_server_logs(self, max_lines=50):
        """Fetch recent server logs from ir.logging or logfile."""
        # 1. Try ir.logging (populated when log_db=True)
        try:
            logs = self.env["ir.logging"].search_read(
                [],
                ["name", "level", "message", "create_date"],
                order="create_date desc",
                limit=max_lines,
            )
            if logs:
                lines = []
                for log in reversed(logs):
                    lines.append(
                        "[{}] [{}] {}: {}".format(
                            log["create_date"],
                            log["level"],
                            log["name"],
                            log["message"],
                        )
                    )
                return "\n".join(lines)
        except Exception as e:
            _logger.warning("Could not fetch ir.logging: %s", e)

        # 2. Fallback: try reading the configured logfile
        for path in [
            "/etc/odoo/odoo-server.log",
            "/var/log/odoo/odoo.log",
        ]:
            try:
                with open(path, "r", errors="replace") as f:
                    lines = f.readlines()
                if lines:
                    return "".join(lines[-max_lines:])
            except (FileNotFoundError, PermissionError):
                continue
            except Exception as e:
                _logger.warning("Could not read %s: %s", path, e)
                continue

        return "(No server logs available)"
