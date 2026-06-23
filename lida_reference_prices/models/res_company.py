from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    reference_pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string="Lista de precios referenciales",
        domain=lambda self: [("currency_id", "!=", self.env.company.currency_id.id)],
    )

    reference_currency_id = fields.Many2one(
        comodel_name='res.currency', related="reference_pricelist_id.currency_id", readonly=False
    )
