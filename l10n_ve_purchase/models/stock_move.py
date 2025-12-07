from odoo import api, fields, models
from odoo.tools.float_utils import float_round


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

    product_price_unit = fields.Float(
        string='Precio Unitario',
        compute='_compute_product_price_unit',
        digits="Product Price",
        store=True,
        help="Obtiene el precio unitario de la línea de pedido de Compra o Venta asociada."
    )

    def _compute_product_price_unit(self):
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

            move.product_price_unit = price

    @api.depends('product_uom_qty', 'location_dest_id')
    def _compute_qty_net_signed(self):
        for move in self:
            # Si el destino es 'supplier' (Proveedor), es una Devolución -> NEGATIVO
            if move.location_dest_id.usage == 'supplier':
                move.qty_net_signed = -move.product_uom_qty
            # Si no, asumimos que es entrada -> POSITIVO
            else:
                move.qty_net_signed = move.product_uom_qty
