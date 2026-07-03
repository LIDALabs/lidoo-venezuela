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
        help="Donde estan las materias primas. Si no se indica, se usa la ubicacion fisica de cada producto.",
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
        string="Ubicacion Virtual",
        compute="_compute_virtual_location_id",
        store=True,
        help="Ubicacion virtual de produccion (auto-detectada).",
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

    # Materias Primas (calculadas desde plantillas)
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
        string="Tiene productos sin plantilla",
        compute="_compute_counts",
    )

    # Filtro de productos (solo los que tienen plantilla)
    product_with_recipe_ids = fields.Many2many(
        "product.product",
        compute="_compute_product_with_recipe_ids",
        store=True,
        depends=["company_id"],
        string="Productos con Plantilla",
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

    @api.depends("company_id")
    def _compute_virtual_location_id(self):
        """Auto-detecta la ubicacion virtual de produccion desde el warehouse.
        Si no existe, la crea automaticamente."""
        for rec in self:
            if not rec.company_id:
                rec.virtual_location_id = False
                continue

            production_loc = False
            warehouse = self.env["stock.warehouse"].search(
                [("company_id", "=", rec.company_id.id)], limit=1
            )
            if warehouse and warehouse.view_location_id:
                # Buscar ubicación de producción hija del almacén
                production_loc = self.env["stock.location"].search(
                    [
                        ("usage", "=", "production"),
                        ("location_id", "child_of", warehouse.view_location_id.id),
                        ("company_id", "=", rec.company_id.id),
                    ],
                    limit=1,
                )
            if not production_loc:
                # Fallback: cualquier ubicación de producción de la empresa
                production_loc = self.env["stock.location"].search(
                    [
                        ("usage", "=", "production"),
                        ("company_id", "=", rec.company_id.id),
                    ],
                    limit=1,
                )
            if not production_loc and warehouse:
                # Crear ubicación de producción si no existe
                production_loc = self.env["stock.location"].create(
                    {
                        "name": _("Producción"),
                        "usage": "production",
                        "location_id": warehouse.view_location_id.id,
                        "company_id": rec.company_id.id,
                    }
                )
            rec.virtual_location_id = production_loc

    @api.depends("finished_product_ids.raw_cost_total")
    def _compute_total_raw_cost(self):
        for rec in self:
            rec.total_raw_cost = sum(
                rec.finished_product_ids.mapped("raw_cost_total")
            )

    def _compute_product_with_recipe_ids(self):
        """Retorna solo los productos que tienen una plantilla activa."""
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

    # Calculo de materias primas desde plantillas
    def action_compute_raw_materials(self):
        """Calcula y llena las materias primas desde las plantillas de todos
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
                        "Los siguientes productos no tienen plantilla definida:\n%s\n"
                        "Cree plantillas en Inventario > Control de Produccion > Plantillas de Productos."
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
            # Validar que todos tengan plantilla
            sin_plantilla = rec.finished_product_ids.filtered(
                lambda l: not l.recipe_id
            )
            if sin_plantilla:
                nombres = "\n".join(
                    f"• {l.product_id.display_name}"
                    for l in sin_plantilla
                )
                raise UserError(
                    _(
                        "Los siguientes productos NO tienen plantilla:\n%s\n\n"
                        "Cree plantillas en Inventario > Control de Produccion "
                        "> Plantillas de Productos."
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

            added_lines = "<br>".join(
                f"• {line.product_id.display_name}: +{line.quantity:.2f} "
                f"{line.product_uom_id.name or ''}"
                for line in rec.finished_product_ids
            )
            removed_lines = "<br>".join(
                f"• {line.product_id.display_name}: -{line.quantity:.2f} "
                f"{line.product_uom_id.name or ''}"
                for line in rec.raw_material_ids
            )
            body = _(
                "Procesado — movimientos de stock creados.<br><br>"
                "<strong>Productos finales agregados:</strong><br>%(added)s<br><br>"
                "<strong>Materias primas descontadas:</strong><br>%(removed)s"
            ) % {"added": added_lines, "removed": removed_lines}
            rec.message_post(
                body=body,
                body_is_html=True,
                subtype_xmlid="mail.mt_comment",
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

    def _get_source_location(self, product):
        """Devuelve la ubicacion de origen para un producto.
        Usa physical_location_id del producto; si no tiene, usa la ubicacion
        principal del almacen de la compania.
        """
        self.ensure_one()
        if product.physical_location_id:
            return product.physical_location_id
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.company_id.id)], limit=1
        )
        return warehouse.lot_stock_id if warehouse else False

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

    def _check_raw_material_availability(self):
        """Valida que haya stock suficiente de cada materia prima."""
        self.ensure_one()
        needed_by_location = {}
        for line in self.raw_material_ids:
            location = self._get_source_location(line.product_id)
            key = (line.product_id.id, location.id if location else False)
            needed_by_location.setdefault(key, {"product": line.product_id, "location": location, "qty": 0.0})
            needed_by_location[key]["qty"] += line.quantity

        shortages = []
        for data in needed_by_location.values():
            product = data["product"]
            location = data["location"]
            qty = data["qty"]
            available = product.with_context(
                location=location.id if location else None
            ).free_qty
            if qty > available:
                shortages.append(
                    _(
                        "• %(product)s: necesita %(need).2f, disponible %(avail).2f"
                    )
                    % {
                        "product": product.display_name,
                        "need": qty,
                        "avail": available,
                    }
                )

        if shortages:
            raise UserError(
                _(
                    "No hay stock suficiente de materias primas:\n%s"
                )
                % "\n".join(shortages)
            )

    def _create_stock_moves(self):
        """Crea movimientos de stock:
        - Producto final: Virtual → Destino (SUMA al inventario)
        - Materia prima: Origen → Virtual (RESTA del inventario)
        """
        self.ensure_one()
        self._validate_locations()
        self._check_raw_material_availability()
        Move = self.env["stock.move"]
        MoveLine = self.env["stock.move.line"]
        virtual_loc = self.virtual_location_id
        dest_loc = self.location_dest_id

        for line in self.finished_product_ids:
            # Salidas: materias primas (Origen → Virtual)
            if line.recipe_id:
                for rline in line.recipe_line_ids:
                    qty_needed = rline.quantity * line.quantity
                    origin_loc = self._get_source_location(rline.product_id)
                    if not origin_loc:
                        raise UserError(
                            _(
                                "No se pudo determinar la ubicacion de origen para '%s'. "
                                "Configure una ubicacion fisica en el producto o un almacen para la compania."
                            )
                            % rline.product_id.display_name
                        )
                    raw_move = Move.create(
                        {
                            "name": f"[{self.name}] Salida: {rline.product_id.display_name}",
                            "origin": self.name,
                            "location_id": origin_loc.id,
                            "location_dest_id": virtual_loc.id,
                            "date": self.date,
                            "company_id": self.company_id.id,
                            "product_id": rline.product_id.id,
                            "product_uom_qty": qty_needed,
                            "price_unit": rline.product_id.standard_price or 0.0,
                            "inventory_calculator_id": self.id,
                        }
                    )
                    MoveLine.create(
                        {
                            "move_id": raw_move.id,
                            "product_id": rline.product_id.id,
                            "product_uom_id": rline.product_uom_id.id,
                            "quantity": qty_needed,
                            "location_id": origin_loc.id,
                            "location_dest_id": virtual_loc.id,
                            "picked": True,
                        }
                    )
                    raw_move._action_confirm()
                    raw_move._action_done()

            # Entrada: producto final (Virtual → Destino)
            move = Move.create(
                {
                    "name": f"[{self.name}] Entrada: {line.product_id.display_name}",
                    "origin": self.name,
                    "location_id": virtual_loc.id,
                    "location_dest_id": dest_loc.id,
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
                    "location_dest_id": dest_loc.id,
                    "picked": True,
                }
            )
            move._action_confirm()
            move._action_done()

    def _create_reverse_stock_moves(self):
        """Invierte todos los movimientos (tanto PF como MP)."""
        self.ensure_one()
        self._validate_locations()
        Move = self.env["stock.move"]
        MoveLine = self.env["stock.move.line"]

        original_moves = self.env["stock.move"].search(
            [
                ("inventory_calculator_id", "=", self.id),
                ("name", "not like", "%Reversa%"),
            ]
        )
        for move in original_moves:
            for mline in move.move_line_ids:
                # Si original era "Entrada", reversa es "Salida" y viceversa
                if "Entrada" in (move.name or ""):
                    tipo_reversa = "Salida"
                else:
                    tipo_reversa = "Entrada"
                reverse_move = Move.create(
                    {
                        "name": f"[{self.name}] Reversa {tipo_reversa}: {move.product_id.display_name}",
                        "origin": self.name,
                        "location_id": mline.location_dest_id.id,
                        "location_dest_id": mline.location_id.id,
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
                        "location_id": mline.location_dest_id.id,
                        "location_dest_id": mline.location_id.id,
                        "picked": True,
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
        tree_view = self.env.ref("l10n_ve_stock.stock_move_calculator_tree_view")
        form_view = self.env.ref("stock.view_move_form")
        return {
            "type": "ir.actions.act_window",
            "name": _("Movimientos"),
            "res_model": "stock.move",
            "views": [(tree_view.id, "tree"), (form_view.id, "form")],
            "domain": [("inventory_calculator_id", "=", self.id)],
            "context": {"default_inventory_calculator_id": self.id},
            "target": "current",
        }

    def action_open_finished_reverse_moves(self):
        self.ensure_one()
        tree_view = self.env.ref("l10n_ve_stock.stock_move_calculator_tree_view")
        form_view = self.env.ref("stock.view_move_form")
        return {
            "type": "ir.actions.act_window",
            "name": _("Movimientos de Reversa"),
            "res_model": "stock.move",
            "views": [(tree_view.id, "tree"), (form_view.id, "form")],
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
