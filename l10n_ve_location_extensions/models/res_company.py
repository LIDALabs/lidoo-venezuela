# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    municipality = fields.Many2one(
        'res.country.municipality',
        'Municipality',
        domain="[('state_id', '=', state_id)]"
    )

    zip_code_id = fields.Many2one(
        'res.country.municipality.zip.code',
        string='Código Postal',
        domain="[('municipality_id', '=', municipality)]"
    )

    @api.onchange('zip_code_id')
    def _onchange_zip_code_id(self):
        for record in self:
            if record.zip_code_id:
                record.zip = record.zip_code_id.name
            else:
                record.zip = False

    @api.onchange('zip')
    def _onchange_zip_manual(self):
        """When zip is typed manually, find or create a matching zip_code_id."""
        for record in self:
            if record.zip and record.municipality:
                zip_code = self.env['res.country.municipality.zip.code'].search([
                    ('name', '=', record.zip),
                    ('municipality_id', '=', record.municipality.id)
                ], limit=1)
                if zip_code:
                    record.zip_code_id = zip_code
                else:
                    record.zip_code_id = self.env['res.country.municipality.zip.code'].create({
                        'name': record.zip,
                        'municipality_id': record.municipality.id,
                    })
            elif not record.zip:
                record.zip_code_id = False
