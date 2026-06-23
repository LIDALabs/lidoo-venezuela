import json
import logging

from odoo import http
from odoo.http import request, route

_logger = logging.getLogger(__name__)


class LidooAnalyticsController(http.Controller):

    @route(
        "/lidoo/analytics/report",
        type="http",
        auth="public",
        methods=["POST", "GET"],
        csrf=False,
        cors=["*"]
    )
    def receive_report(self, **kw):
        """Receive an analytics report from a client instance."""
        try:
            raw_data = request.httprequest.data
            if not raw_data:
                return self._response(
                    {"status": "error", "message": "Empty body"}, 400
                )

            try:
                data = json.loads(raw_data)
            except ValueError:
                return self._response(
                    {"status": "error", "message": "Invalid JSON"}, 400
                )

            # Authenticate via API key
            api_key = data.get("api_key")
            if not api_key:
                return self._response(
                    {"status": "error", "message": "Missing API key"}, 400
                )

            Client = request.env["lidoo.analytics.client"].sudo()
            client = Client.search([("api_key", "=", api_key)], limit=1)

            if not client:
                return self._response(
                    {"status": "error", "message": "Invalid API key"}, 403
                )

            # Update database_uuid if not set
            db_uuid = data.get("database_uuid", "")
            if db_uuid and not client.database_uuid:
                client.database_uuid = db_uuid

            # Create the report record
            Report = request.env["lidoo.analytics.report"].sudo()
            report_vals = {
                "client_id": client.id,
                "odoo_version": data.get("odoo_version", ""),
                "uptime_seconds": data.get("uptime_seconds", 0),
                "database_size": data.get("database_size", 0),
                "active_user_count": data.get("active_user_count", 0),
                "installed_modules": json.dumps(
                    data.get("installed_modules", [])
                ),
                "os_info": data.get("os_info", ""),
                "python_version": data.get("python_version", ""),
                "custom_module_count": data.get("custom_module_count", 0),
                "cpu_usage": data.get("cpu_usage", 0.0),
                "memory_usage": data.get("memory_usage", 0.0),
                "raw_payload": json.dumps(data, default=str),
            }
            Report.create(report_vals)

            # Update client's last report date
            client.last_report_date = request.env[
                "lidoo.analytics.report"
            ]._fields["report_date"].default(Report)

            return self._response(
                {
                    "status": "success",
                    "message": "Report received",
                    "client": client.name,
                }
            )

        except Exception as e:
            _logger.exception("Error receiving analytics report.")
            return self._response(
                {"status": "error", "message": str(e)}, 500
            )

    def _response(self, data, status=200):
        """Helper to return a JSON response."""
        return request.make_response(
            json.dumps(data),
            headers=[("Content-Type", "application/json")],
            status=status,
        )
