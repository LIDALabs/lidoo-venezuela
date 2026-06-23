from odoo import fields, models


class InventoryCalculatorRecipeLog(models.Model):
    _name = "inventory.calculator.recipe.log"
    _description = "Historial de Cambios de Recetas"
    _order = "create_date desc"
    _rec_name = "recipe_id"

    recipe_id = fields.Many2one(
        "inventory.calculator.recipe",
        string="Receta",
        required=True,
        ondelete="cascade",
        index=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Producto",
        related="recipe_id.product_id",
        readonly=True,
    )
    action = fields.Selection(
        [
            ("created", "Creada"),
            ("updated", "Actualizada"),
            ("lines_changed", "Lineas Cambiadas"),
            ("archived", "Archivada"),
            ("unarchived", "Desarchivada"),
        ],
        string="Accion",
        required=True,
    )
    description = fields.Text(string="Detalles")
    user_id = fields.Many2one(
        "res.users",
        string="Usuario",
        default=lambda self: self.env.user,
        readonly=True,
    )
