import secrets
from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit="res.config.settings"

    api_auth_enable_pull = fields.Boolean(
        string="Habilitar modo Pull",
        config_parameter="api_auth.enable_pull",
        help="Permite que el sistema externo consulte y cree datos en esta instancia",
        default=False
    )
    api_auth_pull_api_key = fields.Char(
        string="Clave API (Pull)",
        config_parameter="api_auth.pull_api_key",
        help="Clave usada por el sistema externo para autenticar sus peticiones",
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