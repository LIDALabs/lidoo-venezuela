# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"
