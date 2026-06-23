# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools import float_is_zero, float_round

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    reference_pricelist_id = fields.Many2one(
        string="Lista de Precios Referenciales",
        comodel_name='product.pricelist',
        compute='_compute_reference_pricelist_id',
        store=True
    )

    reference_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='reference_pricelist_id.currency_id',
    )

    reference_pricelist_item_id = fields.Many2one(
        comodel_name='product.pricelist.item',
        compute='_compute_reference_pricelist_id',
        store=True,
    )

    reference_price = fields.Monetary(
        string="Precio Referencial",
        currency_field='reference_currency_id',
        compute='_compute_reference_price',
        readonly=False,
        inverse='_inverse_reference_price',
        help="This is the reference price of the product in the reference pricelist. "
    )

    @api.onchange('list_price')
    def _onchange_list_price(self):
        prices = self._convert_using_reference_currency(self.list_price, inverse=True)
        self.reference_price = prices['reference_price']

        return

    # ocasiona doble edición
    # @api.onchange('reference_price')
    # def _onchange_reference_price(self):
    #     prices = self._convert_using_reference_currency(self.reference_price)
    #     self.list_price = prices['list_price']

    #     return

    def _get_product_attr_for_reference_price_list(self):
        """ Returns the product attributes to be used in the reference price list. """
        self.ensure_one()
        return {
            'applied_on': '1_product',
            'categ_id': False,
            'product_tmpl_id': self.id,
            'product_id': False,
            'base': 'list_price',
            'compute_price': 'fixed',
        }

    def _compute_reference_pricelist_id(self):
        """ Compute the reference pricelist for the product template."""
        PricelistItem = self.env['product.pricelist.item']
        # Rate = self.env['res.currency.rate']
        pricelist = self.env.company.reference_pricelist_id
        if not pricelist:
            return

        # today = fields.Date.today()
        for tmpl in self:
            domain = [
                ('pricelist_id', '=', pricelist.id),
                ('applied_on', '=', '1_product'),
                ('compute_price', '=', 'fixed'),
                ('product_tmpl_id', 'in', tmpl.ids),
            ]
            item_id = tmpl.reference_pricelist_item_id or PricelistItem.search(domain, limit=1)

            tmpl.reference_pricelist_id = pricelist
            tmpl.reference_pricelist_item_id = item_id

    @api.depends('reference_pricelist_id', 'reference_currency_id', 'reference_pricelist_item_id')
    def _compute_reference_price(self):
        """ Compute the reference pricelist for the product template."""
        Rate = self.env['res.currency.rate']
        today = fields.Date.today()
        for tmpl in self:
            if not tmpl.reference_pricelist_id:
                continue

            item_id = tmpl.reference_pricelist_item_id
            if item_id:
                reference_price = item_id.fixed_price if item_id else 0.0
            else:
                rate = Rate.compute_rate(tmpl.reference_currency_id.id, today)['foreign_inverse_rate']
                reference_price = float_round(tmpl.list_price * rate, tmpl.reference_currency_id.decimal_places)

            tmpl.reference_price = reference_price

    def _convert_using_reference_currency(self, reference, inverse=False):
        """
        Convert the given price to the reference currency using the current rate.
        """
        reference_pricelist_id = self.reference_pricelist_id or self.env.company.reference_pricelist_id
        if not reference_pricelist_id:
            return {
                'reference_price': reference,
                'list_price': self.list_price,
            }

        Rate = self.env['res.currency.rate']
        today = fields.Date.today()
        rates = Rate.compute_rate(reference_pricelist_id.currency_id.id, today)
        if inverse:
            rate = rates['foreign_inverse_rate']
            price = float_round(reference, precision_rounding=self.currency_id.rounding)
            reference = float_round(reference * rate, precision_rounding=reference_pricelist_id.currency_id.rounding)
            return {
                'reference_price': reference,
                'list_price': price,
            }

        rate = rates['foreign_rate']
        reference = float_round(reference, precision_rounding=reference_pricelist_id.currency_id.rounding)
        price = float_round(reference * rate, precision_rounding=self.currency_id.rounding)
        return {
            'reference_price': reference,
            'list_price': price,
        }

    @api.depends('reference_currency_id', 'reference_pricelist_item_id')
    def _inverse_reference_price(self):
        """
        Inverse method for reference_price field.
        This method updates the reference price in the reference pricelist item.
        """

        for tmpl in self:
            if not tmpl.reference_pricelist_id:
                continue

            if float_is_zero(tmpl.reference_price, precision_rounding=tmpl.reference_currency_id.rounding):
                prices = tmpl._convert_using_reference_currency(tmpl.list_price, inverse=True)
            else:
                prices = tmpl._convert_using_reference_currency(tmpl.reference_price)

            if not tmpl.reference_pricelist_item_id:
                attrs = tmpl._get_product_attr_for_reference_price_list()
                attrs['pricelist_id'] = tmpl.reference_pricelist_id.id
                attrs['fixed_price'] = prices['reference_price']
                item_id = tmpl.env['product.pricelist.item'].create(attrs)
                tmpl.reference_pricelist_item_id = item_id
            else:
                tmpl.reference_pricelist_item_id.fixed_price = prices['reference_price']
            tmpl.list_price = prices['list_price']

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create method to ensure that the reference pricelist item is created
        when a product template is created.
        """
        reference_pricelist = self.env.company.reference_pricelist_id

        if reference_pricelist:
            for vals in vals_list:
                vals['reference_pricelist_id'] = reference_pricelist.id
                vals['reference_currency_id'] = reference_pricelist.currency_id.id

        records = super().create(vals_list)
        records._inverse_reference_price()

        return records

    # @api.model_create_multi
    # def write(self, vals_list):
    #     """
    #     Override write method to ensure that the reference pricelist item is created
    #     when a product template is created.
    #     """
    #     records = super().write(vals_list)
    #     records._inverse_reference_price()

    #     return records
