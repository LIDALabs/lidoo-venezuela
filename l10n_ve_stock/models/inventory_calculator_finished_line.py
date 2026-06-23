from odoo import api, fields, models


class InventoryCalculatorFinishedLine(models.Model):
    _name = "inventory.calculator.finished.line"
    _description = "Linea de Producto Final"
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
        string="Producto",
        required=True,
        domain="[('id', 'in', parent.product_with_recipe_ids)]",
    )
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unidad",
        related="product_id.uom_id",
        readonly=True,
    )
    quantity = fields.Float(
        string="Cantidad",
        required=True,
        default=1.0,
    )
    note = fields.Text(string="Nota")

    # Receta
    recipe_id = fields.Many2one(
        "inventory.calculator.recipe",
        string="Receta",
        compute="_compute_recipe_id",
        store=True,
    )
    has_recipe = fields.Boolean(
        string="Tiene Receta",
        compute="_compute_recipe_id",
        store=True,
    )
    recipe_line_ids = fields.One2many(
        "inventory.calculator.recipe.line",
        compute="_compute_recipe_line_ids",
        string="Lineas de Receta",
    )

    # Costos
    raw_cost_per_unit = fields.Float(
        string="Costo Unitario Materia Prima",
        compute="_compute_raw_costs",
        store=True,
        digits="Product Price",
    )
    raw_cost_total = fields.Float(
        string="Costo Total Materia Prima",
        compute="_compute_raw_costs",
        store=True,
        digits="Product Price",
    )
    raw_cost_breakdown = fields.Text(
        string="Desglose de Costos",
        compute="_compute_raw_costs",
        store=True,
    )

    # Moneda
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        related="calculator_id.currency_id",
        readonly=True,
    )

    @api.depends("product_id")
    def _compute_recipe_id(self):
        Recipe = self.env["inventory.calculator.recipe"]
        for line in self:
            recipe = Recipe.search(
                [("product_id", "=", line.product_id.id), ("active", "=", True)],
                limit=1,
            )
            line.recipe_id = recipe
            line.has_recipe = bool(recipe)

    @api.depends("recipe_id", "quantity")
    def _compute_recipe_line_ids(self):
        for line in self:
            if line.recipe_id:
                line.recipe_line_ids = line.recipe_id.line_ids
            else:
                line.recipe_line_ids = self.env[
                    "inventory.calculator.recipe.line"
                ]

    @api.depends("recipe_line_ids", "quantity")
    def _compute_raw_costs(self):
        for line in self:
            if not line.recipe_line_ids:
                line.raw_cost_per_unit = 0.0
                line.raw_cost_total = 0.0
                line.raw_cost_breakdown = ""
                continue

            total = 0.0
            breakdown_parts = []
            for rline in line.recipe_line_ids:
                cost = rline.quantity * (rline.product_id.standard_price or 0.0)
                total += cost
                if rline.product_id.standard_price:
                    breakdown_parts.append(
                        f"• {rline.product_id.display_name}: "
                        f"{rline.quantity} x {rline.product_id.standard_price:.2f} = {cost:.2f}"
                    )

            line.raw_cost_per_unit = total
            line.raw_cost_total = total * line.quantity
            line.raw_cost_breakdown = (
                "\n".join(breakdown_parts) if breakdown_parts else ""
            )
