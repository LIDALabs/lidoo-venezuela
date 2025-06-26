from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    withholding_type_id = fields.Many2one(default=lambda self: self.env.ref('l10n_ve_payment_extension.account_withholding_type_75'))

    @api.onchange("prefix_vat", "vat")
    def _onchange_prefix_vat(self):
        if self.type_person_id or not self.prefix_vat or not self.vat:
            return

        if self.prefix_vat in ('J', 'G', 'C'):
            self.type_person_id = self.env.ref('l10n_ve_payment_extension.type_person_three_l10n_ve_payment_extension').id

        elif self.prefix_vat in ('P'):
            self.type_person_id = self.env.ref('l10n_ve_payment_extension.type_person_two_l10n_ve_payment_extension').id

        elif self.prefix_vat in ('V'):
            self.type_person_id = self.env.ref('l10n_ve_payment_extension.type_person_l10n_ve_payment_extension').id
