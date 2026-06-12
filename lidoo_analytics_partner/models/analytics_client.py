import json
import logging
import uuid

import requests
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LidooAnalyticsClient(models.Model):
    _name = "lidoo.analytics.client"
    _description = "Analytics Client"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(
        string="Client Name",
        required=True,
        tracking=True,
    )
    database_uuid = fields.Char(
        string="Database UUID",
        readonly=True,
        help="Automatically populated from the first received report.",
        tracking=True,
    )
    api_key = fields.Char(
        string="API Key",
        readonly=True,
        copy=False,
        help="Auto-generated key. Share this with the client for authentication.",
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Contact",
        tracking=True,
    )
    last_report_date = fields.Datetime(
        string="Last Report",
        readonly=True,
    )
    status = fields.Selection(
        [
            ("active", "Active"),
            ("warning", "Warning"),
            ("inactive", "Inactive"),
        ],
        string="Status",
        compute="_compute_status",
        store=True,
    )
    report_ids = fields.One2many(
        "lidoo.analytics.report",
        "client_id",
        string="Reports",
    )
    alert_ids = fields.One2many(
        "lidoo.analytics.alert",
        "client_id",
        string="Alerts",
    )
    report_count = fields.Integer(
        string="Report Count",
        compute="_compute_report_count",
    )
    endpoint_url = fields.Char(
        string="Endpoint URL",
        compute="_compute_endpoint_url",
        help="Share this URL with the client to configure their analytics settings.",
    )

    sync_mode = fields.Selection(
        [("push", "Push"), ("pull", "Pull")],
        string="Sync Mode",
        default="push",
        required=True,
        help="Push: Client sends data. Pull: Partner fetches data.",
    )
    base_target_url = fields.Char(
        string="Base Target URL",
        help="Base URL of the client analytics endpoint (e.g. https://client.odoo.com)",
    )
    target_url = fields.Char(
        string="Target URL",
        compute="_compute_target_url",
    )
    pull_api_key = fields.Char(
        string="Pull API Key",
        help="API Key provided by the client for Pull authentication.",
    )

    @api.depends("last_report_date")
    def _compute_status(self):
        now = fields.Datetime.now()
        for record in self:
            if not record.last_report_date:
                record.status = "inactive"
            else:
                delta = now - record.last_report_date
                hours = delta.total_seconds() / 3600
                if hours <= 24:
                    record.status = "active"
                elif hours <= 48:
                    record.status = "warning"
                else:
                    record.status = "inactive"

    def _compute_report_count(self):
        for record in self:
            record.report_count = len(record.report_ids)

    def _compute_endpoint_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        for record in self:
            record.endpoint_url = f"{base_url}/lidoo/analytics/report"

    @api.depends("base_target_url")
    def _compute_target_url(self):
        for record in self:
            if not record.base_target_url:
                record.target_url = False
            elif record.base_target_url.endswith('/'):
                record.target_url =  f"{record.base_target_url}lidoo/analytics/status" 
            else:
                record.target_url = f"{record.base_target_url}/api/lidoo/analytics/status"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("api_key"):
                vals["api_key"] = str(uuid.uuid4())
        return super().create(vals_list)

    def action_regenerate_api_key(self):
        """Allow the manager to regenerate the API key."""
        for record in self:
            record.api_key = str(uuid.uuid4())
        return True

    def _pull_report(self):
        self.ensure_one()
        if self.sync_mode != 'pull' or not self.target_url or not self.pull_api_key:
            return False

        try:
            headers = {
                'X-Lidoo-Api-Key': self.pull_api_key,
                'Accept': '*/*',
                'User-Agent': 'Lidoo-Analytics',
            }

            try:
                response = requests.get(self.target_url, headers=headers, timeout=30)
            except requests.exceptions.RequestException as e:
                _logger.warning(f"Failed to pull report from {self.name}: {e}")
                return False

            if response.status_code != 200:
                _logger.warning(f"Failed to pull report from {self.name}: HTTP {response.status_code}")
                return False

            json_response = response.json()
            if json_response.get('status') != 'success':
                _logger.warning(f"Failed to pull report from {self.name}: API returned error {json_response.get('message')}")
                return False

            data = json_response.get('data', {})

            # Update DB UUID
            db_uuid = data.get("database_uuid", "")
            if db_uuid and not self.database_uuid:
                self.database_uuid = db_uuid

            # Create Report
            report_vals = {
                "client_id": self.id,
                "odoo_version": data.get("odoo_version", ""),
                "uptime_seconds": data.get("uptime_seconds", 0),
                "database_size": data.get("database_size", 0),
                "active_user_count": data.get("active_user_count", 0),
                "installed_modules": json.dumps(data.get("installed_modules", [])),
                "os_info": data.get("os_info", ""),
                "python_version": data.get("python_version", ""),
                "custom_module_count": data.get("custom_module_count", 0),
                "cpu_usage": data.get("cpu_usage", 0.0),
                "memory_usage": data.get("memory_usage", 0.0),
                "raw_payload": json.dumps(data, default=str),
                "lidoo_commit_hash": data.get("lidoo_commit_hash", ""),
            }
            res = self.env["lidoo.analytics.report"].create(report_vals)

            # Update Last Report
            self.last_report_date = res.report_date
            _logger.info(f"Successfully pulled report for client {self.name}")
            return True

        except Exception as e:
            _logger.exception(f"Error pulling report from {self.name}")
            return False

    @api.model
    def _cron_pull_reports(self):
        clients = self.search([('sync_mode', '=', 'pull')])
        for client in clients:
            client._pull_report()

    def action_fetch_now(self):
        self.ensure_one()
        if self._pull_report():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Report fetched successfully',
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Error',
                    'message': 'Failed to fetch report. See logs for details.',
                    'type': 'danger',
                    'sticky': False,
                }
            }
