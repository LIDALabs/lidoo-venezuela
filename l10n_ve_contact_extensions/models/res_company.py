from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    validate_user_creation_general = fields.Boolean(default=True)

    l10n_ve_vat = fields.Char(related='partner_id.l10n_ve_vat', store=True)
    l10n_ve_vat_formatted = fields.Char(related='partner_id.l10n_ve_vat_formatted', store=True)
