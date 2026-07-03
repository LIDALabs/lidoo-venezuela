import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InventoryCalculatorRecipe(models.Model):
    _name = "inventory.calculator.recipe"
    _description = "Plantilla de Producto"
    _order = "product_id"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Nombre de la Plantilla",
        required=True,
        tracking=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Producto Final",
        required=True,
        tracking=True,
    )
    product_uom_id = fields.Many2one(
        "uom.uom",
        string="Unidad",
        related="product_id.uom_id",
        readonly=True,
    )
    active = fields.Boolean(
        string="Plantilla Activa",
        default=True,
        tracking=True,
    )
    note = fields.Text(string="Notas")
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )

    line_ids = fields.One2many(
        "inventory.calculator.recipe.line",
        "recipe_id",
        string="Materia Prima",
        copy=True,
    )
    raw_material_count = fields.Integer(
        string="Materiales",
        compute="_compute_raw_material_count",
    )
    log_count = fields.Integer(
        string="Cambios",
        compute="_compute_log_count",
    )

    @api.depends("line_ids")
    def _compute_raw_material_count(self):
        for rec in self:
            rec.raw_material_count = len(rec.line_ids)

    def _compute_log_count(self):
        Log = self.env["inventory.calculator.recipe.log"]
        for rec in self:
            rec.log_count = Log.search_count([("recipe_id", "=", rec.id)])

    @api.constrains("product_id")
    def _check_unique_product(self):
        for rec in self:
            existing = self.search(
                [
                    ("product_id", "=", rec.product_id.id),
                    ("active", "=", True),
                    ("id", "!=", rec.id),
                ]
            )
            if existing:
                raise UserError(
                    _(
                        "Ya existe una plantilla activa para el producto '%s'. "
                        "Archive la plantilla existente primero."
                    )
                    % rec.product_id.display_name
                )

    def action_view_history(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Historial de Cambios"),
            "res_model": "inventory.calculator.recipe.log",
            "view_mode": "tree,form",
            "domain": [("recipe_id", "=", self.id)],
            "context": {"default_recipe_id": self.id},
            "target": "current",
        }

    def action_archive(self):
        for rec in self:
            rec._log_action("archived")
            rec.active = False

    def action_unarchive(self):
        for rec in self:
            rec._log_action("unarchived")
            rec.active = True

    def _log_action(self, action, description=""):
        Log = self.env["inventory.calculator.recipe.log"]
        for rec in self:
            Log.create(
                {
                    "recipe_id": rec.id,
                    "product_id": rec.product_id.id,
                    "action": action,
                    "description": description,
                    "user_id": self.env.user.id,
                }
            )

    @api.model_create_multi
    def create(self, vals_list):
        recipes = super().create(vals_list)
        for recipe in recipes:
            recipe._log_action("created", f"Plantilla '{recipe.name}' creada para {recipe.product_id.display_name}")
        return recipes

    def write(self, vals):
        result = super().write(vals)
        if "line_ids" in vals:
            for rec in self:
                rec._log_action("lines_changed", "Lineas de materia prima actualizadas")
        elif any(k in vals for k in ("name", "product_id")):
            for rec in self:
                rec._log_action("updated", f"Campos actualizados: {', '.join(vals.keys())}")
        return result


class InventoryCalculatorRecipeLine(models.Model):
    _name = "inventory.calculator.recipe.line"
    _description = "Linea de Plantilla"
    _order = "sequence, id"

    sequence = fields.Integer(string="Secuencia", default=10)
    recipe_id = fields.Many2one(
        "inventory.calculator.recipe",
        string="Plantilla",
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
        string="Cantidad por Unidad",
        required=True,
        help="Cantidad de materia prima necesaria por 1 unidad de producto final.",
    )
