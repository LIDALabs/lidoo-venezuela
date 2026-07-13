import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    default_account_receivable_id = fields.Many2one(
        "account.account",
        string="Cuenta por cobrar predeterminada",
        domain="[('account_type', '=', 'asset_receivable'), ('deprecated', '=', False)]",
        help="Cuenta por cobrar predeterminada para nuevos contactos",
    )
    default_account_payable_id = fields.Many2one(
        "account.account",
        string="Cuenta por pagar predeterminada",
        domain="[('account_type', '=', 'liability_payable'), ('deprecated', '=', False)]",
        help="Cuenta por pagar predeterminada para nuevos contactos",
    )

    def _localization_use_documents(self):
        self.ensure_one()
        return self.account_fiscal_country_id.code == "VE" or super(ResCompany, self)._localization_use_documents()

    def _propagate_default_accounts_to_contacts(self):
        """Propaga las cuentas por defecto a todos los contactos de la empresa."""
        for company in self:
            vals = {}
            if company.default_account_receivable_id:
                vals["property_account_receivable_id"] = company.default_account_receivable_id.id
            if company.default_account_payable_id:
                vals["property_account_payable_id"] = company.default_account_payable_id.id
            if vals:
                contacts = self.env["res.partner"].search([("company_id", "=", company.id)])
                if contacts:
                    contacts.write(vals)
