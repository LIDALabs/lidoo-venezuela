from odoo import fields, api, models, _
from odoo.tools.float_utils import float_round


class FlowMetrics(models.Model):
    _name = "flow.metrics"
    _description = "Flow Metrics"

    product_id = fields.Many2one('product.product', 'Producto', readonly=True)
    product_selection = fields.Selection([
        ('specific', 'Producto específico'),
        ('all', 'Todos los productos'),
    ], string='Selección de producto', default='specific', readonly=True)

    report_type = fields.Selection([
        ('both', 'Ambas'),
        ('purchases', 'Solo Compras'),
        ('sales', 'Solo Ventas'),
    ], string='Mostrar en el reporte', default='both', readonly=True)

    product_uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', string='Unidad', readonly=True)

    date_from = fields.Date('Desde', readonly=True)
    date_to = fields.Date('Hasta', readonly=True)

    qty_sold = fields.Float('Vendido', compute='_compute_sold')
    qty_sold_return = fields.Float('Ventas Devueltas', compute='_compute_sold_return')
    qty_sold_net = fields.Float('Neto de las Ventas', compute='_compute_sold_net')

    qty_purchased = fields.Float('Comprado', compute='_compute_purchased')
    qty_purchased_return = fields.Float('Compras Devueltas', compute='_compute_purchased_return')
    qty_purchased_net = fields.Float('Neto de las Compras', compute="_compute_purchased_net")

    standard_price_ves = fields.Float('Costo Unitario Compra (VES)', compute='_compute_prices')
    standard_price_usd = fields.Float('Costo Unitario Compra (USD)', compute='_compute_prices')
    sale_price_ves = fields.Float('Costo Unitario Venta (VES)', compute='_compute_prices')
    sale_price_usd = fields.Float('Costo Unitario Venta (USD)', compute='_compute_prices')
    total_purchased_ves = fields.Float('Total Compras (VES)', compute='_compute_prices')
    total_purchased_usd = fields.Float('Total Compras (USD)', compute='_compute_prices')
    total_sold_ves = fields.Float('Total Ventas (VES)', compute='_compute_prices')
    total_sold_usd = fields.Float('Total Ventas (USD)', compute='_compute_prices')

    def _get_common_domain(self):
        return [
            ('date', '>=', self[:1].date_from),
            ('date', '<=', self[:1].date_to),
            ('state', '=', 'done'),
        ]

    @api.depends('product_id', 'date_from', 'date_to')
    def _compute_purchased(self):
        product_ids = self.mapped('product_id').ids
        if not product_ids:
            for rec in self:
                rec.qty_purchased = 0
            return

        domain = self._get_common_domain() + [
            ('product_id', 'in', product_ids),
            ('purchase_line_id', '!=', False),
        ]

        raw_data = self.env['stock.move']._read_group(
            domain, ['product_id'], ['product_uom_qty:sum'],
        )
        product_data = {product.id: qty_sum for product, qty_sum in raw_data}

        for rec in self:
            rec.qty_purchased = product_data.get(rec.product_id.id, 0)

    @api.depends('product_id', 'date_from', 'date_to')
    def _compute_purchased_return(self):
        product_ids = self.mapped('product_id').ids
        if not product_ids:
            for rec in self:
                rec.qty_purchased_return = 0
            return

        domain = self._get_common_domain() + [
            ('product_id', 'in', product_ids),
            ('purchase_line_id', '!=', False),
            ('location_dest_id.usage', '!=', 'internal'),
        ]

        raw_data = self.env['stock.move']._read_group(
            domain, ['product_id'], ['product_uom_qty:sum'],
        )
        product_data = {product.id: qty_sum for product, qty_sum in raw_data}

        for rec in self:
            rec.qty_purchased_return = product_data.get(rec.product_id.id, 0)

    @api.depends('product_id', 'date_from', 'date_to')
    def _compute_sold(self):
        product_ids = self.mapped('product_id').ids
        if not product_ids:
            for rec in self:
                rec.qty_sold = 0
            return

        domain = self._get_common_domain() + [
            ('product_id', 'in', product_ids),
            ('location_dest_id.usage', '=', 'customer'),
            ('location_id.usage', '=', 'internal'),
        ]

        raw_data = self.env['stock.move']._read_group(
            domain, ['product_id'], ['product_uom_qty:sum'],
        )
        product_data = {product.id: qty_sum for product, qty_sum in raw_data}

        for rec in self:
            rec.qty_sold = product_data.get(rec.product_id.id, 0)

    @api.depends('product_id', 'date_from', 'date_to')
    def _compute_sold_return(self):
        product_ids = self.mapped('product_id').ids
        if not product_ids:
            for rec in self:
                rec.qty_sold_return = 0
            return

        domain = self._get_common_domain() + [
            ('product_id', 'in', product_ids),
            ('location_dest_id.usage', '=', 'internal'),
            ('location_id.usage', '=', 'customer'),
        ]

        raw_data = self.env['stock.move']._read_group(
            domain, ['product_id'], ['product_uom_qty:sum'],
        )
        product_data = {product.id: qty_sum for product, qty_sum in raw_data}

        for rec in self:
            rec.qty_sold_return = product_data.get(rec.product_id.id, 0)

    @api.depends('qty_sold', 'qty_sold_return')
    def _compute_sold_net(self):
        for rec in self:
            net = rec.qty_sold - rec.qty_sold_return
            rec.qty_sold_net = float_round(net, precision_digits=0)

    @api.depends('qty_purchased', 'qty_purchased_return')
    def _compute_purchased_net(self):
        for rec in self:
            net = rec.qty_purchased - rec.qty_purchased_return
            rec.qty_purchased_net = float_round(net, precision_digits=0)

    @api.depends('product_id', 'date_from', 'date_to', 'qty_purchased', 'qty_sold')
    def _compute_prices(self):
        company = self.env.company
        foreign_currency = company.currency_foreign_id

        rate_usd = 0.0
        if foreign_currency:
            try:
                rate_data = self.env['res.currency.rate'].compute_rate(
                    foreign_currency.id, self[:1].date_to or fields.Date.today()
                )
                rate_usd = rate_data.get('foreign_rate', 0.0) or 0.0
            except Exception:
                rate_usd = 0.0

        for rec in self:
            purchase_unit_price_ves = 0.0
            sale_unit_price_ves = 0.0

            purchase_moves = self.env['stock.move'].search([
                ('product_id', '=', rec.product_id.id),
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
                ('state', '=', 'done'),
                ('purchase_line_id', '!=', False),
            ])

            if purchase_moves:
                total_value = 0.0
                total_qty = 0.0
                for move in purchase_moves:
                    if move.price_unit:
                        total_value += move.price_unit * move.product_uom_qty
                        total_qty += move.product_uom_qty
                    elif move.purchase_line_id:
                        total_value += move.purchase_line_id.price_unit * move.product_uom_qty
                        total_qty += move.product_uom_qty
                if total_qty:
                    purchase_unit_price_ves = total_value / total_qty

            sale_moves = self.env['stock.move'].search([
                ('product_id', '=', rec.product_id.id),
                ('date', '>=', rec.date_from),
                ('date', '<=', rec.date_to),
                ('state', '=', 'done'),
                ('sale_line_id', '!=', False),
            ])

            if sale_moves:
                total_value = 0.0
                total_qty = 0.0
                for move in sale_moves:
                    if move.price_unit:
                        total_value += move.price_unit * move.product_uom_qty
                        total_qty += move.product_uom_qty
                    elif move.sale_line_id:
                        total_value += move.sale_line_id.price_unit * move.product_uom_qty
                        total_qty += move.product_uom_qty
                if total_qty:
                    sale_unit_price_ves = total_value / total_qty

            purchase_unit_price_usd = purchase_unit_price_ves / rate_usd if rate_usd else 0.0
            sale_unit_price_usd = sale_unit_price_ves / rate_usd if rate_usd else 0.0

            rec.standard_price_ves = purchase_unit_price_ves
            rec.standard_price_usd = purchase_unit_price_usd
            rec.sale_price_ves = sale_unit_price_ves
            rec.sale_price_usd = sale_unit_price_usd
            rec.total_purchased_ves = purchase_unit_price_ves * rec.qty_purchased
            rec.total_purchased_usd = purchase_unit_price_usd * rec.qty_purchased
            rec.total_sold_ves = sale_unit_price_ves * rec.qty_sold
            rec.total_sold_usd = sale_unit_price_usd * rec.qty_sold

    def action_print_pdf(self):
        return self.env.ref('l10n_ve_product_flow_metrics.action_report_flow_metrics').report_action(self)
