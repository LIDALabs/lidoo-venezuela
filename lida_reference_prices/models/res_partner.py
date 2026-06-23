from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    property_product_pricelist = fields.Many2one(default=lambda self: self.env.ref('lida_reference_prices.base_price_pricelist', raise_if_not_found=False))
