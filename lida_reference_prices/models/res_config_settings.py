from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    reference_pricelist_id = fields.Many2one(
        comodel_name='product.pricelist', related="company_id.reference_pricelist_id", readonly=False
    )
