from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    taxpayer_type = fields.Selection(
        [
            ("formal", "Formal"),
            ("special", "Special"),
            ("ordinary", "Ordinary"),
        ],
        default="special",
        tracking=True,
    )

    vat = fields.Char(
        string="RIF",
        tracking=True,
    )

    street = fields.Char(tracking=True)

    country_id = fields.Many2one(
        tracking=True,
        default=lambda self: self.env["res.country"].search([("code", "=", "VE")], limit=1),
    )

    l10n_ve_default_customer_payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Término de pago por defecto (cliente)",
        help="Término de pago que se usará por defecto en facturas de cliente "
             "cuando el contacto no tenga uno configurado.",
        check_company=True,
    )

    l10n_ve_default_vendor_payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Término de pago por defecto (proveedor)",
        help="Término de pago que se usará por defecto en facturas de proveedor "
             "cuando el contacto no tenga uno configurado.",
        check_company=True,
    )
