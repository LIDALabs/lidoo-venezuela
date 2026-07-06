from odoo import api, fields, models


class InventoryCalculatorRawLine(models.Model):
    _name = "inventory.calculator.raw.line"
    _description = "Linea de Materia Prima"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)
    calculator_id = fields.Many2one(
        "inventory.calculator",
        string="Calculadora",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Materia Prima",
        required=True,
    )
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unidad",
        related="product_id.uom_id",
        readonly=True,
    )
    quantity = fields.Float(
        string="Cantidad Necesaria",
        required=True,
    )
    available_qty = fields.Float(
        string="Cantidad Disponible",
        compute="_compute_available_qty",
    )
    unit_cost = fields.Float(
        string="Costo/Unit",
        compute="_compute_unit_cost",
    )
    total_cost = fields.Float(
        string="Costo Total",
        compute="_compute_total_cost",
    )
    note = fields.Text(string="Nota")

    company_id = fields.Many2one(
        "res.company",
        related="calculator_id.company_id",
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="calculator_id.currency_id",
        readonly=True,
    )

    @api.depends("product_id")
    def _compute_unit_cost(self):
        for line in self:
            line.unit_cost = line.product_id.standard_price if line.product_id else 0.0

    @api.depends("unit_cost", "quantity")
    def _compute_total_cost(self):
        for line in self:
            line.total_cost = line.unit_cost * line.quantity

    @api.depends("product_id")
    def _compute_available_qty(self):
        for line in self:
            if line.product_id:
                # Usar el stock disponible total del producto (calculado por Odoo)
                line.available_qty = line.product_id.qty_available
            else:
                line.available_qty = 0.0
