import secrets
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    lidoo_analytics_enabled = fields.Boolean(
        string="Enable Partner Analytics",
        config_parameter="lidoo_analytics.enabled",
        default=False,
    )
    lidoo_analytics_endpoint_url = fields.Char(
        string="Partner Endpoint URL",
        config_parameter="lidoo_analytics.endpoint_url",
        default="",
    )
    lidoo_analytics_api_key = fields.Char(
        string="API Key",
        config_parameter="lidoo_analytics.api_key",
        default="",
    )
    lidoo_analytics_interval_hours = fields.Integer(
        string="Reporting Interval (hours)",
        config_parameter="lidoo_analytics.interval_hours",
        default=8,
    )
    lidoo_analytics_collect_hw = fields.Boolean(
        string="Collect Hardware Metrics",
        help="Enable collection of CPU, RAM, and disk metrics. Requires psutil.",
        config_parameter="lidoo_analytics.collect_hw",
        default=False,
    )

    lidoo_analytics_enable_pull = fields.Boolean(
        string="Enable Pull Mode",
        config_parameter="lidoo_analytics.enable_pull",
        default=False,
        help="Allow the partner instance to pull analytics data from this instance.",
    )
    lidoo_analytics_pull_api_key = fields.Char(
        string="Pull API Key",
        config_parameter="lidoo_analytics.pull_api_key",
        default="",
        readonly=True,
        help="Key used by the partner instance to authenticate pull requests.",
    )

    def action_generate_pull_key(self):
        """Generate a secure random key for Pull Mode and save it immediately."""
        new_key = secrets.token_bytes(32).hex()
        self.env['ir.config_parameter'].set_param('lidoo_analytics.pull_api_key', new_key)
        # Return a reload action to update the view
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
