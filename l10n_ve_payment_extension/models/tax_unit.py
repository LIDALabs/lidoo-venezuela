from odoo import _, api, fields, models

#: Factor proveniente del Decreto 1.808 - Art 9, Parágrafo Segundo - G.O. 36.203
SENIAT_FACTOR_PN = 83.3334


class TaxUnit(models.Model):
    _name = "tax.unit"
    _inherit = "tax.unit"
    _description = "Tax Unit"
