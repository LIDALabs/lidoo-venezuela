import logging

from odoo import _, api, fields, models
from ...tools import binaural_bcv_query

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit="sale.order"

    show_currency = fields.Boolean(
        string="Cotizacion en USD",
        default=False,
        help="Los precios de la cotizacion se mostran en dolares"
    )

    dollar_currency_rate = fields.Float(
        string="Tasa USD",
        digits=(16,2),
        compute='_compute_currency',
        help="Tasa de cambio calculada para mostrar en el PDF"
    )

    dollar_currency_id = fields.Many2one(
        string="Moneda USD",
        comodel_name='res.currency',
        compute='_compute_currency',
        store=True,
        help="Moneda que se mostrara en el PDF"
    )

    dollar_amount_taxe_subtotal = fields.Monetary(
        string="Subtotal Tax USD (PDF)",
        currency_field="dollar_currency_id",
        compute="_compute_taxes",
        help="Subtotal convertido a USD"
    )

    dollar_amount_taxe_total = fields.Monetary(
        string="Total Tax USD (PDF)",
        currency_field="dollar_currency_id",
        compute="_compute_taxes",
        help="Total convertido a USD"
    )

    dollar_amount_taxe_tax = fields.Monetary(
        string="Tax USD (PDF)",
        currency_field="dollar_currency_id",
        compute="_compute_taxes",
        help="Impuesto convertidos a USD"
    )

    @api.depends('show_currency', 'date_order')
    def _compute_currency(self):

        for order in self:
            if not order.show_currency:
                order.dollar_currency_id = False
                order.dollar_currency_rate = 1.0
            ...

            use_currency = self.env.ref('base.USD')
            order.dollar_currency_id = use_currency

            try:
                rates, rate_day = binaural_bcv_query.get_bcv_rate_of_the_day(self)
                order.dollar_currency_rate=rates.get('USD', 1.0)
                ...
            except Exception:
                order.dollar_currency_rate = 1.0                
        ...

    @api.depends('dollar_currency_rate', 'amount_untaxed', 'amount_total', 'amount_tax')
    def _compute_taxes(self):
        for order in self: 
            if not order.show_currency:
                order.dollar_amount_taxe_subtotal= 0
                order.dollar_amount_taxe_total= 0
                order.dollar_amount_taxe_tax = 0
                ...
            order.dollar_amount_taxe_subtotal = order.amount_untaxed / order.dollar_currency_rate
            order.dollar_amount_taxe_total = order.amount_total / order.dollar_currency_rate
            order.dollar_amount_taxe_tax = order.amount_tax / order.dollar_currency_rate
        ...