from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    withholding_type_id = fields.Many2one(default=lambda self: self.env.ref('l10n_ve_payment_extension.account_withholding_type_75'))
    type_person_id = fields.Many2one(compute='_compute_type_person_id', inverse='_inverse_type_person_id')

    @api.depends('prefix_vat', "vat")
    def _compute_type_person_id(self):
        pj_domiciliada = self.env.ref('l10n_ve_payment_extension.type_person_three_l10n_ve_payment_extension')
        pn_no_residente = self.env.ref('l10n_ve_payment_extension.type_person_two_l10n_ve_payment_extension')
        pn_residente = self.env.ref('l10n_ve_payment_extension.type_person_l10n_ve_payment_extension')

        for p in self:
            if not p.prefix_vat or not p.vat:
                continue

            if p.prefix_vat in ('J', 'G', 'C'):
                p.type_person_id = pj_domiciliada.id

            elif p.prefix_vat in ('P'):
                p.type_person_id = pn_no_residente.id

            elif p.prefix_vat in ('V', 'E'):
                p.type_person_id = pn_residente.id

    def _inverse_type_person_id(self):
        pass