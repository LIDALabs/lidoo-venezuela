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
    note = fields.Text(string="Nota")

    company_id = fields.Many2one(
        "res.company",
        related="calculator_id.company_id",
        readonly=True,
    )

    @api.depends("product_id", "calculator_id.location_src_id")
    def _compute_available_qty(self):
        for line in self:
            if line.product_id and line.calculator_id.location_src_id:
                quants = self.env["stock.quant"].search(
                    [
                        ("product_id", "=", line.product_id.id),
                        (
                            "location_id",
                            "=",
                            line.calculator_id.location_src_id.id,
                        ),
                    ]
                )
                line.available_qty = sum(quants.mapped("quantity"))
            else:
                line.available_qty = 0.0
