from odoo import _, api, fields, models

class StockMove(models.Model):
    _inherit = "stock.move"
    _order = "priority_location asc"

    priority_location = fields.Integer(
        string="Priority", related="product_id.priority_location", store=True
    )
    inventory_calculator_id = fields.Many2one(
        "inventory.calculator",
        string="Calculadora de Inventario",
        ondelete="set null",
        index=True,
    )
