
from odoo import fields, api, models, _
from odoo.tools.float_utils import float_round
from dateutil.relativedelta import relativedelta

class FlowMetricsWizard(models.TransientModel): 
    _name = "flow.metrics.wizard"
    _description = "Solo para seleccionar el producto, para posterior ver los datos e imprimir el PDF"
  
    # ------------------------------    
    # Valores por defectos de las fechas
    # Son los ultioms 30 dias
    def _get_default_date_from(self):
        # ultimos 30 dias
        return ( fields.Datetime.now() - relativedelta(months=1) )
        ...

    def _get_defualt_date_to(self): 
        # dia de hoy
        return fields.Datetime.now()
        ...
    # ------------------------------
        
    product_selection = fields.Selection([
        ('specific', 'Producto específico'),
        ('all', 'Todos los productos'),
    ], string='Selección de producto', default='specific', required=True)

    product_id = fields.Many2one(
        'product.product',
        "Producto",
    )

    only_with_moves = fields.Boolean(
        'Solo productos con compras o ventas',
        default=False,
    )

    report_type = fields.Selection([
        ('both', 'Ambas'),
        ('purchases', 'Solo Compras'),
        ('sales', 'Solo Ventas'),
    ], string='Mostrar en el reporte', default='both', required=True)

    date_from = fields.Date('Desde', default=_get_default_date_from, required=True)
    date_to = fields.Date('Hasta', default=_get_defualt_date_to, required=True)

    @api.onchange('product_selection')
    def _onchange_product_selection(self):
        if self.product_selection == 'all':
            self.product_id = False

    def _get_products_domain(self):
        domain = []
        if self.only_with_moves:
            purchase_moves = self.env['stock.move'].search_read(
                [
                    ('date', '>=', self.date_from),
                    ('date', '<=', self.date_to),
                    ('state', '=', 'done'),
                    ('purchase_line_id', '!=', False),
                ],
                ['product_id'],
            )
            sale_moves = self.env['stock.move'].search_read(
                [
                    ('date', '>=', self.date_from),
                    ('date', '<=', self.date_to),
                    ('state', '=', 'done'),
                    ('sale_line_id', '!=', False),
                ],
                ['product_id'],
            )
            active_ids = set()
            for move in purchase_moves:
                if move['product_id']:
                    active_ids.add(move['product_id'][0])
            for move in sale_moves:
                if move['product_id']:
                    active_ids.add(move['product_id'][0])
            domain = [('id', 'in', list(active_ids))]
        return domain

    def action_sent_result(self): 
        self.ensure_one()

        if self.product_selection == 'specific' and not self.product_id:
            return {'type': 'ir.actions.act_window_close'}

        if self.product_selection == 'specific':
            metrics = self.env['flow.metrics'].create({
                'product_id': self.product_id.id,
                'product_selection': 'specific',
                'report_type': self.report_type,
                'date_from': self.date_from,
                'date_to': self.date_to,
            })

            return {
                'name': 'Reporte de Movimiento',
                'type': 'ir.actions.act_window',
                'res_model': 'flow.metrics',
                'view_mode': 'form',
                'res_id': metrics.id,
                'target': 'current',
            }
        else:
            domain = self._get_products_domain()
            products = self.env['product.product'].search(domain)

            if not products:
                return {'type': 'ir.actions.act_window_close'}

            metrics_records = self.env['flow.metrics']
            for product in products:
                metrics = self.env['flow.metrics'].create({
                    'product_id': product.id,
                    'product_selection': 'all',
                    'report_type': self.report_type,
                    'date_from': self.date_from,
                    'date_to': self.date_to,
                })
                metrics_records |= metrics

            return self.env.ref(
                'l10n_ve_product_flow_metrics.action_report_flow_metrics'
            ).report_action(metrics_records)
    ...

