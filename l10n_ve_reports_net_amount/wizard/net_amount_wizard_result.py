from odoo import fields, api, models, _
from odoo.tools.float_utils import float_round


class NetAmountWizardResult(models.TransientModel):
    _name = "net.amount.wizard.result"

    product_id = fields.Many2one('product.product', 'Producto', readonly=True)

    date_from = fields.Date('Desde', readonly=True)
    date_to = fields.Date('Hasta', readonly=True)

    qty_sold = fields.Float('Vendido', compute='_compute_sold')
    qty_sold_return = fields.Float('Vendidos Devueltas', compute='_compute_sold_return')
    
    qty_purchased = fields.Float('Comprado', compute='_compute_purchased')
    qty_purchased_return = fields.Float('Compras Devueltas', compute='_compute_purchased_return')

    @api.depends('product_id', 'date_from', 'date_to')
    def _compute_purchased(self):
        raw_data = self.env['stock.move']._read_group(
            [
                ('product_id', '=', self.product_id.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('location_dest_id.usage', '=', 'internal'),
                ('location_id.usage', '=', 'supplier'),
                ('state', '=', 'done'),
            ],
            ['product_id'],
            ['product_uom_qty:sum'],
        )

        product_purchased_qty_data = {
            product.id: qty_sum
            for product, qty_sum in raw_data
        }

        # print('Purchased:')
        # print(raw_data)
        # print('//--------//')

        for producto in self:
            purchased_qty = product_purchased_qty_data.get(producto.product_id.id, 0)
            producto.qty_purchased = purchased_qty
    ...

    @api.depends('product_id', 'date_from', 'date_to')
    def _compute_purchased_return(self):
        raw_data = self.env['stock.move']._read_group(
            [
                ('product_id', '=', self.product_id.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('location_dest_id.usage', '=', 'supplier'),
                ('location_id.usage', '=', 'internal'),
                ('state', '=', 'done'),
            ],
            ['product_id'],
            ['product_uom_qty:sum'],
        )

        product_purchased_return_qty_data = {
            product.id: qty_sum
            for product, qty_sum in raw_data
        }

        # print('Purchased Return')
        # print(raw_data)
        # print('//----//')

        for producto in self:
            purchased_return_qty = product_purchased_return_qty_data.get(producto.product_id.id, 0)
            producto.qty_purchased_return = purchased_return_qty
            ...
        ...

    @api.depends('product_id', 'date_from', 'date_to')
    def _compute_sold(self):
        raw_data = self.env['stock.move']._read_group(
            [
                ('product_id', '=', self.product_id.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('location_dest_id.usage', '=', 'customer'),
                ('location_id.usage', '=', 'internal'),
                ('state', '=', 'done'),
            ],
            ['product_id'],
            ['product_uom_qty:sum'],
        )

        product_sold_qty_data = {
            product.id: qty_sum
            for product, qty_sum in raw_data
        }

        # print('Sold')
        # print(raw_data)
        # print('//----//')

        for producto in self:
            sold_qty = product_sold_qty_data.get(producto.product_id.id, 0)
            producto.qty_sold = sold_qty
            ...
        ...

    @api.depends('product_id', 'date_from', 'date_to')
    def _compute_sold_return(self):
        raw_data = self.env['stock.move']._read_group(
            [
                ('product_id', '=', self.product_id.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
                ('location_dest_id.usage', '=', 'internal'),
                ('location_id.usage', '=', 'customer'),
                ('state', '=', 'done'),
            ],
            ['product_id'],
            ['product_uom_qty:sum'],
        )

        product_sold_return_qty_data = {
            product.id: qty_sum
            for product, qty_sum in raw_data
        }

        # print('Sold Return')
        # print(raw_data)
        # print('///------//')

        for producto in self:
            sold_return_qty = product_sold_return_qty_data.get(producto.product_id.id, 0)
            producto.qty_sold_return = sold_return_qty
            ...
        ...
    

    def action_print_pdf(self):
        
        self.ensure_one()

        return self.env.ref('l10n_ve_reports_net_amount.action_report_net_amount').report_action(self)


