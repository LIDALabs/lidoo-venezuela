import secrets
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit="res.config.settings"

    api_auth_enable_pull = fields.Boolean(
        string="Enable Pull Mode",
        config_parameter="api_auth.enable_pull",
        help="Allow the partner instance to pull data from this instance",
        default=False
    )
    api_auth_pull_api_key = fields.Char(
        string="Pull Api Key",
        config_parameter="api_auth.pull_api_key",
        help="Key used by the partner instance to authenticate pull requests",
        default="",
        readonly=True
    )

    def action_generate_api_auth_pull_key(self):
        """Generate a secure random key for Pull Mode and save it immediately."""
        new_key = secrets.token_bytes(32).hex()
        self.env['ir.config_parameter'].set_param('api_auth.pull_api_key', new_key)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }