from odoo import api, fields, models, _
from odoo.exceptions import UserError


class InventoryCalculatorProcess(models.TransientModel):
    _name = "inventory.calculator.process"
    _description = "Procesar Calculadora de Inventario"

    calculator_id = fields.Many2one(
        "inventory.calculator",
        string="Calculadora",
        required=True,
        readonly=True,
    )
    virtual_location_id = fields.Many2one(
        "stock.location",
        string="Ubicacion Virtual (Traslado)",
        domain="[('usage', 'in', ('transit', 'view'))]",
        required=True,
        help="Ubicacion de transito usada como intermediario durante la produccion.",
    )
    location_dest_id = fields.Many2one(
        "stock.location",
        string="Ubicacion Destino",
        domain="[('usage', '=', 'internal')]",
        required=True,
        help="Donde se almacenan los productos finales.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        default=lambda self: self.env.company,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get("active_id")
        if active_id:
            calculator = self.env["inventory.calculator"].browse(active_id)
            res.setdefault("calculator_id", calculator.id)
            res.setdefault("virtual_location_id",
                           calculator.virtual_location_id.id)
            res.setdefault("location_dest_id",
                           calculator.location_dest_id.id)
        return res

    def action_process(self):
        self.ensure_one()
        if not self.calculator_id:
            raise UserError(_("No se encontro la calculadora."))
        calculator = self.calculator_id
        calculator.virtual_location_id = self.virtual_location_id
        calculator.location_dest_id = self.location_dest_id
        calculator.action_done()
        return {"type": "ir.actions.act_window_close"}

    def action_cancel(self):
        self.ensure_one()
        if not self.calculator_id:
            raise UserError(_("No se encontro la calculadora."))
        self.calculator_id.action_cancel()
        return {"type": "ir.actions.act_window_close"}
