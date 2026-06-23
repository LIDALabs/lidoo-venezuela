import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InventoryCalculator(models.Model):
    _name = "inventory.calculator"
    _description = "Produccion"
    _order = "date desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(
        string="Referencia",
        required=True,
        readonly=True,
        default="/",
        copy=False,
    )
    date = fields.Date(
        string="Fecha",
        required=True,
        default=fields.Date.context_today,
        tracking=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsable",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("confirmed", "Confirmado"),
            ("done", "Procesado"),
            ("cancelled", "Cancelado"),
        ],
        string="Estado",
        default="draft",
        readonly=True,
        tracking=True,
    )
    note = fields.Text(string="Notas")
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        related="company_id.currency_id",
        readonly=True,
    )

    # Ubicaciones
    location_src_id = fields.Many2one(
        "stock.location",
        string="Ubicacion Origen",
        domain="[('usage', '=', 'internal')]",
        help="Ubicacion de referencia para materias primas (opcional).",
    )
    location_dest_id = fields.Many2one(
        "stock.location",
        string="Ubicacion Destino",
        required=True,
        domain="[('usage', '=', 'internal')]",
        help="Donde se almacenan los productos finales.",
    )
    virtual_location_id = fields.Many2one(
        "stock.location",
        string="Ubicacion Virtual (Traslado)",
        domain="[('usage', 'in', ('transit', 'view'))]",
        help="Ubicacion de transito usada como intermediario durante la produccion.",
    )

    # Productos Finales (input del usuario)
    finished_product_ids = fields.One2many(
        "inventory.calculator.finished.line",
        "calculator_id",
        string="Productos Finales",
        copy=True,
        tracking=True,
    )
    finished_product_count = fields.Integer(
        string="Productos Finales",
        compute="_compute_counts",
    )

    # Materias Primas (calculadas desde recetas)
    raw_material_ids = fields.One2many(
        "inventory.calculator.raw.line",
        "calculator_id",
        string="Materias Primas",
        readonly=True,
        tracking=True,
    )
    raw_material_count = fields.Integer(
        string="Materias Primas",
        compute="_compute_counts",
    )
    has_raw_without_recipe = fields.Boolean(
        string="Tiene productos sin receta",
        compute="_compute_counts",
    )

    # Filtro de productos (solo los que tienen receta)
    product_with_recipe_ids = fields.Many2many(
        "product.product",
        compute="_compute_product_with_recipe_ids",
        string="Productos con Receta",
    )

    # Resumen de costos
    total_raw_cost = fields.Float(
        string="Costo Total Materia Prima",
        compute="_compute_total_raw_cost",
        store=True,
        digits="Product Price",
        help="Suma de los costos de materias primas para todos los productos finales.",
    )

    # Movimientos de Stock (trazabilidad)
    finished_move_ids = fields.Many2many(
        "stock.move",
        compute="_compute_finished_move_ids",
        string="Movimientos de Productos Finales",
    )
    finished_move_count = fields.Integer(
        string="Movimientos",
        compute="_compute_finished_move_ids",
    )
    finished_reverse_move_ids = fields.Many2many(
        "stock.move",
        compute="_compute_finished_reverse_move_ids",
        string="Movimientos de Reversa",
    )

    def _compute_counts(self):
        for rec in self:
            rec.raw_material_count = len(rec.raw_material_ids)
            rec.finished_product_count = len(rec.finished_product_ids)
            rec.has_raw_without_recipe = any(
                not line.recipe_id for line in rec.finished_product_ids
            )

    @api.depends("finished_product_ids.raw_cost_total")
    def _compute_total_raw_cost(self):
        for rec in self:
            rec.total_raw_cost = sum(
                rec.finished_product_ids.mapped("raw_cost_total")
            )

    def _compute_product_with_recipe_ids(self):
        """Retorna solo los productos que tienen una receta activa."""
        Recipe = self.env["inventory.calculator.recipe"]
        recipe_products = Recipe.sudo().search([("active", "=", True)]).mapped(
            "product_id"
        )
        for rec in self:
            rec.product_with_recipe_ids = recipe_products

    def _compute_finished_move_ids(self):
        for rec in self:
            moves = self.env["stock.move"].search(
                [("inventory_calculator_id", "=", rec.id)]
            )
            rec.finished_move_ids = moves
            rec.finished_move_count = len(moves)

    def _compute_finished_reverse_move_ids(self):
        for rec in self:
            moves = self.env["stock.move"].search(
                [
                    ("inventory_calculator_id", "=", rec.id),
                    ("name", "like", "%Reversa%"),
                ]
            )
            rec.finished_reverse_move_ids = moves

    # CRUD
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "inventory.calculator"
                ) or "/"
        return super().create(vals_list)

    def write(self, vals):
        if vals and not self.env.context.get("bypass_calculator_protection"):
            for rec in self:
                if rec.state in ("done", "cancelled"):
                    raise UserError(
                        _(
                            "No puede editar el registro %(name)s porque "
                            "esta en estado '%(state)s'."
                        )
                        % {"name": rec.name, "state": rec.state}
                    )
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.state not in ("draft", "cancelled"):
                raise UserError(
                    _(
                        "No puede eliminar el registro %(name)s porque "
                        "esta en estado '%(state)s'. Cancelelo primero."
                    )
                    % {"name": rec.name, "state": rec.state}
                )
        return super().unlink()

    # Calculo de materias primas desde recetas
    def action_compute_raw_materials(self):
        """Calcula y llena las materias primas desde las recetas de todos
        los productos finales."""
        for rec in self:
            if not rec.finished_product_ids:
                raise UserError(
                    _("Agregue al menos un producto final primero.")
                )

            # Agrupar materias primas de todos los productos finales
            aggregated = {}
            missing = []

            for fline in rec.finished_product_ids:
                if not fline.recipe_id:
                    missing.append(fline.product_id.display_name)
                    continue

                for rline in fline.recipe_line_ids:
                    prod = rline.product_id
                    needed = rline.quantity * fline.quantity
                    if prod.id in aggregated:
                        aggregated[prod.id]["quantity"] += needed
                    else:
                        aggregated[prod.id] = {
                            "product_id": prod.id,
                            "product_uom_id": rline.product_uom_id.id,
                            "quantity": needed,
                        }

            if missing:
                raise UserError(
                    _(
                        "Los siguientes productos no tienen receta definida:\n%s\n"
                        "Cree recetas en Inventario > Control de Produccion > Recetas de Productos."
                    )
                    % "\n".join(f"• {name}" for name in missing)
                )

            # Construir nuevas lineas de materia prima
            new_lines = []
            for data in aggregated.values():
                new_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": data["product_id"],
                            "product_uom_id": data["product_uom_id"],
                            "quantity": data["quantity"],
                        },
                    )
                )

            # Reemplazar todas las lineas de materia prima
            rec.with_context(bypass_calculator_protection=True).write(
                {"raw_material_ids": [(5, 0, 0)] + new_lines}
            )

            rec.message_post(
                body=_(
                    "Materias primas calculadas: %d productos, %d materias primas."
                )
                % (len(rec.finished_product_ids), len(new_lines)),
                subtype_xmlid="mail.mt_note",
            )

    # Flujo de trabajo
    def action_confirm(self):
        for rec in self:
            if not rec.finished_product_ids:
                raise UserError(
                    _("Agregue al menos un producto final.")
                )
            # Validar que todos tengan receta
            sin_receta = rec.finished_product_ids.filtered(
                lambda l: not l.recipe_id
            )
            if sin_receta:
                nombres = "\n".join(
                    f"• {l.product_id.display_name}"
                    for l in sin_receta
                )
                raise UserError(
                    _(
                        "Los siguientes productos NO tienen receta:\n%s\n\n"
                        "Cree recetas en Inventario > Control de Produccion "
                        "> Recetas de Productos."
                    )
                    % nombres
                )
            if not rec.raw_material_ids:
                rec.action_compute_raw_materials()
            rec.state = "confirmed"
            rec.message_post(
                body=_("Confirmado por %s") % rec.user_id.name,
                subtype_xmlid="mail.mt_note",
            )

    def action_done(self):
        for rec in self:
            if rec.state != "confirmed":
                raise UserError(_("Solo los registros confirmados pueden procesarse."))
            rec._create_stock_moves()
            rec.state = "done"
            rec.message_post(
                body=_("Procesado — movimientos de stock creados."),
                subtype_xmlid="mail.mt_note",
            )

    def action_cancel(self):
        for rec in self:
            if rec.state == "done":
                rec._create_reverse_stock_moves()
                rec.message_post(
                    body=_("Cancelado desde Procesado — movimientos de reversa creados."),
                    subtype_xmlid="mail.mt_comment",
                )
            elif rec.state in ("draft", "confirmed"):
                rec.message_post(
                    body=_("Cancelado por %s") % rec.user_id.name,
                    subtype_xmlid="mail.mt_note",
                )
            rec.state = "cancelled"

    def action_draft(self):
        for rec in self:
            if rec.state == "done":
                raise UserError(
                    _("Los registros procesados no pueden volver a borrador. Cancelelo primero.")
                )
            if rec.state == "cancelled" and rec.finished_reverse_move_ids:
                raise UserError(
                    _(
                        "No puede volver a borrador — este registro tiene "
                        "movimientos de reversa. Cree un nuevo registro."
                    )
                )
            rec.state = "draft"
            rec.message_post(
                body=_("Vuelto a borrador."),
                subtype_xmlid="mail.mt_note",
            )

    # Creacion de movimientos de stock
    def _validate_locations(self):
        """Valida que las ubicaciones requeridas esten configuradas."""
        self.ensure_one()
        errors = []
        if not self.virtual_location_id:
            errors.append(_("Ubicacion Virtual de Produccion"))
        if not self.location_dest_id:
            errors.append(_("Ubicacion Destino"))
        if errors:
            raise UserError(
                _(
                    "Debe configurar las siguientes ubicaciones antes "
                    "de procesar:\n• %s"
                )
                % "\n• ".join(errors)
            )

    def _create_stock_moves(self):
        """Crea un stock.move por cada producto final (patron Odoo 17).

        IMPORTANTE: Las materias primas NO se descuentan del stock.
        La calculadora solo AGREGA productos finales al inventario.
        """
        self.ensure_one()
        self._validate_locations()
        Move = self.env["stock.move"]
        MoveLine = self.env["stock.move.line"]
        virtual_loc = self.virtual_location_id

        for line in self.finished_product_ids:
            move = Move.create(
                {
                    "name": f"[{self.name}] {line.product_id.display_name}",
                    "origin": self.name,
                    "location_id": virtual_loc.id,
                    "location_dest_id": self.location_dest_id.id,
                    "date": self.date,
                    "company_id": self.company_id.id,
                    "product_id": line.product_id.id,
                    "product_uom_qty": line.quantity,
                    "price_unit": line.product_id.standard_price or 0.0,
                    "inventory_calculator_id": self.id,
                }
            )
            MoveLine.create(
                {
                    "move_id": move.id,
                    "product_id": line.product_id.id,
                    "product_uom_id": line.product_uom_id.id,
                    "quantity": line.quantity,
                    "location_id": virtual_loc.id,
                    "location_dest_id": self.location_dest_id.id,
                }
            )
            move._action_confirm()
            move._action_done()

    def _create_reverse_stock_moves(self):
        """Invierte cada movimiento de producto final individualmente."""
        self.ensure_one()
        self._validate_locations()
        Move = self.env["stock.move"]
        MoveLine = self.env["stock.move.line"]
        virtual_loc = self.virtual_location_id

        original_moves = self.env["stock.move"].search(
            [
                ("inventory_calculator_id", "=", self.id),
                ("name", "not like", "%Reversa%"),
            ]
        )
        for move in original_moves:
            for mline in move.move_line_ids:
                reverse_move = Move.create(
                    {
                        "name": f"[{self.name}] {move.product_id.display_name} Reversa",
                        "origin": self.name,
                        "location_id": self.location_dest_id.id,
                        "location_dest_id": virtual_loc.id,
                        "date": fields.Date.context_today(self),
                        "company_id": self.company_id.id,
                        "product_id": move.product_id.id,
                        "product_uom_qty": mline.quantity,
                        "price_unit": move.price_unit,
                        "inventory_calculator_id": self.id,
                    }
                )
                MoveLine.create(
                    {
                        "move_id": reverse_move.id,
                        "product_id": move.product_id.id,
                        "product_uom_id": mline.product_uom_id.id,
                        "quantity": mline.quantity,
                        "location_id": self.location_dest_id.id,
                        "location_dest_id": virtual_loc.id,
                    }
                )
                reverse_move._action_confirm()
                reverse_move._action_done()

    # Acciones auxiliares
    def action_open_finished_products(self):
        """Abre la lista de productos finales de esta calculadora."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Productos Finales"),
            "res_model": "inventory.calculator.finished.line",
            "view_mode": "tree,form",
            "domain": [("calculator_id", "=", self.id)],
            "context": {
                "default_calculator_id": self.id,
            },
            "target": "current",
        }

    def action_open_raw_materials(self):
        """Abre la lista de materias primas de esta calculadora."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Materias Primas"),
            "res_model": "inventory.calculator.raw.line",
            "view_mode": "tree,form",
            "domain": [("calculator_id", "=", self.id)],
            "context": {
                "default_calculator_id": self.id,
            },
            "target": "current",
        }

    def action_open_finished_moves(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Movimientos de Productos Finales"),
            "res_model": "stock.move",
            "view_mode": "tree,form",
            "domain": [("inventory_calculator_id", "=", self.id)],
            "context": {"default_inventory_calculator_id": self.id},
            "target": "current",
        }

    def action_open_finished_reverse_moves(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Movimientos de Reversa"),
            "res_model": "stock.move",
            "view_mode": "tree,form",
            "domain": [
                ("inventory_calculator_id", "=", self.id),
                ("name", "like", "%Reversa%"),
            ],
            "target": "current",
        }

    # Reportes
    def print_report_pdf(self):
        self.ensure_one()
        return self.env.ref(
            "l10n_ve_stock.action_report_inventory_calculator_pdf"
        ).report_action(self)

    def print_report_xlsx(self):
        self.ensure_one()
        return self.env.ref(
            "l10n_ve_stock.action_report_inventory_calculator_xlsx"
        ).report_action(self)
