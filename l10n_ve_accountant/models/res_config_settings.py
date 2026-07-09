from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ve_default_customer_payment_term_id = fields.Many2one(
        "account.payment.term",
        related="company_id.l10n_ve_default_customer_payment_term_id",
        readonly=False,
        string="Término de pago por defecto (cliente)",
    )

    l10n_ve_default_vendor_payment_term_id = fields.Many2one(
        "account.payment.term",
        related="company_id.l10n_ve_default_vendor_payment_term_id",
        readonly=False,
        string="Término de pago por defecto (proveedor)",
    )
