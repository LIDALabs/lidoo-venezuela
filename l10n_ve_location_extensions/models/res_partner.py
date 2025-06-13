# -*- coding: utf-8 -*-
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    city = fields.Char(string="City related",
                       related="municipality.name", store=True)

    municipality = fields.Many2one("res.country.municipality", "Municipality", domain="[('state_id', '=', state_id)]")
