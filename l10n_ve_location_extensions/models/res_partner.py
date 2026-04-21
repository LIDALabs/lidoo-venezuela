# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    city = fields.Char(string="City related",
                       related="municipality.name", store=True)

    municipality = fields.Many2one("res.country.municipality", "Municipality", domain="[('state_id', '=', state_id)]")
    
    zip_code_id = fields.Many2one(
        "res.country.municipality.zip.code", 
        string="Código Postal", 
        domain="[('municipality_id', '=', municipality)]"
    )

    @api.onchange('zip_code_id')
    def _onchange_zip_code_id(self):
        for record in self:
            if record.zip_code_id:
                record.zip = record.zip_code_id.name
