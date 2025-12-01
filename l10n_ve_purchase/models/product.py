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

    @api.depends('purchased_product_qty') # Dependemos del campo original de Odoo
    def _compute_purchased_net_qty(self):
        for product in self:
            domain = [
                ('product_id', '=', product.id),
                ('state', '=', 'done'),
                ('location_dest_id.usage', '=', 'supplier'),
                ('location_id.usage', '=', 'internal'),
                ('purchase_line_id', '!=', False) 
            ]
            moves = self.env['stock.move'].search(domain)
            returned_qty = sum(move.product_uom_qty for move in moves)
            
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

class StockMove(models.Model):
    _inherit = 'stock.move'

    # Campo visual para mostrar positivo si es compra, negativo si es devolución
    qty_net_signed = fields.Float(
        string="Cantidad Neta", 
        compute='_compute_qty_net_signed',
        digits='Product Unit of Measure'
    )

    currency_id = fields.Many2one(
        'res.currency', 
        related='company_id.currency_id', 
        string='Moneda de la Compañía', 
        readonly=True
    )

    compute_price_unit = fields.Float(
        string='Precio Unitario',
        compute='_compute_price_unit',
        digits="Product Price",
        store=True,
        help="Obtiene el precio unitario de la línea de pedido de Compra o Venta asociada."
    )

    def _compute_price_unit(self):
        has_purchase = 'purchase.order.line' in self.env
        has_sale = 'sale.order.line' in self.env
    
        for move in self: 
            price = 0.0

            # Verificamos si el campo purchase_line_id existe ANTES de usarlo
            purchase_line = getattr(move, 'purchase_line_id', False)
            sale_line = getattr(move, 'sale_line_id', False)
            
            if has_purchase and purchase_line:
                # Si el módulo purchase está instalado y hay línea de compra
                price = purchase_line.price_unit

            elif has_sale and sale_line:
                # Si el módulo sale está instalado y hay línea de venta
                price = sale_line.price_unit
            
            if not price and move.product_id:
                price = move.product_id.standard_price

            move.compute_price_unit = price
        ...

    @api.depends('product_uom_qty', 'location_dest_id')
    def _compute_qty_net_signed(self):
        for move in self:
            # Si el destino es 'supplier' (Proveedor), es una Devolución -> NEGATIVO
            if move.location_dest_id.usage == 'supplier':
                move.qty_net_signed = -move.product_uom_qty
            # Si no, asumimos que es entrada -> POSITIVO
            else:
                move.qty_net_signed = move.product_uom_qty