# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    country_id = fields.Many2one(
        'res.country',
        default=lambda self: self.env.ref('base.ve')
    )
    l10n_ve_vat = fields.Char('Venezuelan VAT', index=True, compute="_compute_l10n_ve_vat", store=True)
    l10n_ve_vat_formatted = fields.Char('Venezuelan VAT Formatted', index=True, compute="_compute_l10n_ve_vat", store=True)

    @api.onchange("prefix_vat")
    def _onchange_prefix_vat(self):
        if not self.prefix_vat:
            return

        if self.prefix_vat in ('J', 'G', 'C'):
            self.company_type = 'company'
        else:
            self.company_type = 'person'

    @api.constrains('vat', 'country_id', 'prefix_vat')
    def check_vat(self):
        """ Since we validate more documents than the vat for Venezuelan partners (RIF, CI) we
        extend this method in order to process it. """
        if self.env.company.country_code != 'VE':
            return super(ResPartner, self).check_vat()

        l10n_ve_partners = self.filtered(lambda x: x.country_code == 'VE')
        l10n_ve_partners.l10n_ve_identification_validation()
        return super(ResPartner, self - l10n_ve_partners).check_vat()

    def l10n_ve_identification_validation(self):
        person_vat_pattern = "^[0-9]{1,9}$"
        enterprise_vat_pattern = "^[0-9]{9}$"
        for partner in self:
            # TODO: Permitir saltar esta validación según el contexto.
            # En este punto puede que el partner se este creando como parte de un usuario y en el formulario de usuario no hay forma de agregar VAT.
            # En los formularios adecuados estos campos son requeridos.
            if not partner.prefix_vat or not partner.vat:
                continue
            # if not partner.user_ids and not partner.prefix_vat:
            #     raise ValidationError(_("Debe indicar el tipo de CI/RIF"))
            # if not partner.user_ids and not partner.vat:
            #     raise ValidationError(_("Debe indicar el CI/RIF"))

            if partner.prefix_vat in ('V', 'E'):
                if partner.vat and not (re.match(person_vat_pattern, partner.vat)):
                    raise ValidationError(_("The vat field only accepts numbers and must be between 1 and 9 digits"))
            elif partner.vat and not re.match(enterprise_vat_pattern, partner.vat):
                raise ValidationError(_("The vat field only accepts numbers and must be 9 digits long"))

    def check_duplicate_email(self, email, company_id=None):
        if email and (self.env.company.validate_user_creation_general or self.env.company.validate_user_creation_by_company):
            domain = [
                ("email", "=", email),
                ("id", "!=", self.id if self else False),
            ]

            if self.env.company.validate_user_creation_by_company:
                domain.extend(
                    [
                        ("company_id", "=", company_id or self.env.company.id),
                    ]
                )
                error_message = _(
                    "A partner with the same email address already exists for this company."
                )
            elif self.env.company.validate_user_creation_general:
                error_message = _(
                    "A partner with the same email already exists.")
            else:
                error_message = _(
                    "A partner with the same email address already exists for this company."
                )

            existing_partner = self.env["res.partner"].search(domain, limit=1)
            if existing_partner:
                raise ValidationError(error_message)

    @api.depends('prefix_vat', 'vat')
    def _compute_l10n_ve_vat(self):
        for partner in self:
            if partner.country_code == 'VE' and partner.prefix_vat and partner.vat:
                partner.l10n_ve_vat = "%s%s" % (partner.prefix_vat, partner.vat)
                if len(partner.vat) < 9:
                    partner.l10n_ve_vat_formatted = "%s-%s" % (partner.prefix_vat, partner.vat)
                else:
                    partner.l10n_ve_vat_formatted = "%s-%s-%s" % (partner.prefix_vat, partner.vat[:-1], partner.vat[-1])
