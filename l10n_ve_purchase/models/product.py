from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # 1. Campo para calcular devoluciones (Lo que ya teníamos)
    purchased_returned_qty = fields.Float(
        compute='_compute_purchased_net_qty',
        string='Devoluciones',
        digits='Product Unit of Measure',
        help="Cantidad devuelta a proveedores."
    )

    # 2. Campo NUEVO: La resta (Comprado - Devuelto)
    purchased_net_qty = fields.Float(
        compute='_compute_purchased_net_qty',
        string='Comprado (Neto)',
        digits='Product Unit of Measure',
        help="Cantidad comprada menos las devoluciones."
    )

    @api.depends('purchased_product_qty')  # Dependemos del campo original de Odoo
    def _compute_purchased_net_qty(self):
        raw_data = self.env['stock.move']._read_group(
            [
                ('product_id', 'in', self.ids),
                ('state', '=', 'done'),
                ('location_dest_id.usage', '=', 'supplier'),
                ('location_id.usage', '=', 'internal'),
                ('purchase_line_id', '!=', False)
            ],
            ['product_id'],
            ['product_uom_qty:sum']
        )

        product_returned_qty_data = {
            product.id: qty_sum
            for product, qty_sum in raw_data
        }

        for product in self:
            returned_qty = product_returned_qty_data.get(product.id, 0)

            # Guardamos la devolución
            product.purchased_returned_qty = float_round(
                returned_qty,
                precision_rounding=product.uom_id.rounding
            )

            # --- B. Calcular Neto (La resta que pediste) ---
            # purchased_product_qty es el campo nativo de Odoo (Total Pedido/Recibido)
            product.purchased_net_qty = float_round(
                product.purchased_product_qty - returned_qty,
                precision_rounding=product.uom_id.rounding
            )


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    purchased_returned_qty = fields.Float(
        compute='_compute_purchased_net_qty',
        string='Devoluciones',
        digits='Product Unit of Measure'
    )

    purchased_net_qty = fields.Float(
        compute='_compute_purchased_net_qty',
        string='Comprado (Neto)',
        digits='Product Unit of Measure'
    )

    @api.depends('product_variant_ids.purchased_net_qty')
    def _compute_purchased_net_qty(self):
        for template in self:
            # Sumamos los valores de todas las variantes
            total_returned = sum(p.purchased_returned_qty for p in template.product_variant_ids)
            total_net = sum(p.purchased_net_qty for p in template.product_variant_ids)

            template.purchased_returned_qty = float_round(
                total_returned,
                precision_rounding=template.uom_id.rounding
            )
            template.purchased_net_qty = float_round(
                total_net,
                precision_rounding=template.uom_id.rounding
            )

    def action_view_net_purchases(self):
        """ 
        Abre una vista de movimientos de stock filtrando 
        compras y devoluciones de este producto 
        """
        self.ensure_one()

        # Buscamos el ID de la vista que creamos en el XML
        tree_view_id = self.env.ref('l10n_ve_purchase.view_stock_move_net_purchase_tree').id
        # NOTA: Reemplaza 'nombre_de_tu_modulo' por el nombre técnico de tu carpeta de módulo.

        return {
            'name': 'Movimientos Netos de Compra',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            # Aquí indicamos explícitamente que use nuestra vista tree
            'views': [[tree_view_id, 'tree'], [False, 'form']],
            'domain': [
                ('product_id', 'in', self.product_variant_ids.ids),
                ('state', '=', 'done'),
                '|',
                '&', ('location_id.usage', '=', 'supplier'), ('location_dest_id.usage', '=', 'internal'),
                '&', ('location_id.usage', '=', 'internal'), ('location_dest_id.usage', '=', 'supplier'),
            ],
            # 'context': {'search_default_by_product': 1},
        }
