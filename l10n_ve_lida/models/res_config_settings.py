from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    default_account_receivable_id = fields.Many2one(
        "account.account",
        related="company_id.account_receivable_id",
        readonly=False,
        default_model="res.company",
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False)]",
    )
    default_account_payable_id = fields.Many2one(
        "account.account",
        related="company_id.account_payable_id",
        readonly=False,
        default_model="res.company",
        domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False)]",
    )

    def action_apply_default_accounts_to_contacts(self):
        """Aplica las cuentas por defecto a todos los contactos de la empresa."""
        self.company_id._propagate_default_accounts_to_contacts()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Cuentas actualizadas",
                "message": "Las cuentas por defecto se aplicaron a todos los contactos de la empresa.",
                "sticky": False,
                "type": "success",
            },
        }
