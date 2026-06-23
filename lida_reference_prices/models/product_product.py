# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools import float_is_zero, float_round

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    ref_pricelist_item_id = fields.Many2one(
        comodel_name='product.pricelist.item',
        compute='_compute_ref_pricelist_id',
        store=True,
    )

    ref_price = fields.Monetary(
        string="Precio Referencial",
        currency_field='reference_currency_id',
        compute='_compute_ref_price',
        readonly=False,
        inverse='_inverse_ref_price',
        help="This is the reference price of the product in the reference pricelist. "
    )

    @api.onchange('lst_price')
    def _onchange_lst_price(self):
        prices = self.product_tmpl_id._convert_using_reference_currency(self.lst_price, inverse=True)
        self.ref_price = prices['reference_price']

        return False

    # ocasiona doble edición
    # @api.onchange('ref_price')
    # def _onchange_ref_price(self):
    #     if self.env.context.get('update_ref_price', False):
    #         return False
    #     prices = self.product_tmpl_id._convert_using_reference_currency(self.ref_price)
    #     self.lst_price = prices['list_price']

    #     return False

    def _get_product_attr_for_reference_price_list(self):
        """ Returns the product attributes to be used in the reference price list. """
        self.ensure_one()
        return {
            'applied_on': '0_product_variant',
            'categ_id': False,
            'product_tmpl_id': self.product_tmpl_id.id,
            'product_id': self.id,
            'base': 'list_price',
            'compute_price': 'fixed',
        }

    @api.depends('reference_pricelist_id', 'company_id.reference_pricelist_id')
    def _compute_ref_pricelist_id(self):
        """ Compute the reference pricelist for the product product."""
        PricelistItem = self.env['product.pricelist.item']
        # Rate = self.env['res.currency.rate']
        pricelist = self.reference_pricelist_id
        if not pricelist:
            return

        # today = fields.Date.today()
        for product in self:
            item_id = PricelistItem.search([
                ('pricelist_id', '=', pricelist.id),
                ('applied_on', '=', '0_product_variant'),
                ('compute_price', '=', 'fixed'),
                ('product_id', 'in', product.ids),
            ], limit=1)
            # if not item_id:
            #     rate = Rate.compute_rate(pricelist.currency_id.id, today)['foreign_inverse_rate']
            #     reference_price = float_round(product.list_price * rate, pricelist.currency_id.decimal_places)
            #     attrs = product._get_product_attr_for_reference_price_list()
            #     attrs.update({
            #         'product_tmpl_id': product._uid,
            #         'pricelist_id': pricelist.id,
            #         'fixed_price': reference_price,
            #     })
            #     item_id = PricelistItem.create(attrs)
            product.ref_pricelist_item_id = item_id

    @api.depends('list_price', 'reference_pricelist_id', 'reference_currency_id', 'ref_pricelist_item_id')
    def _compute_ref_price(self):
        """ Compute the reference pricelist for the product variant."""
        Rate = self.env['res.currency.rate']
        today = fields.Date.today()
        for product in self:
            if not product.reference_pricelist_id:
                continue

            item_id = product.ref_pricelist_item_id
            if item_id:
                reference_price = item_id.fixed_price if item_id else 0.0
            else:
                rate = Rate.compute_rate(product.reference_currency_id.id, today)['foreign_inverse_rate']
                reference_price = float_round(product.lst_price * rate, product.reference_currency_id.decimal_places)

            product.ref_price = reference_price

    @api.depends('reference_currency_id')
    def _inverse_ref_price(self):
        """
        Inverse method for ref_price field.
        This method updates the reference price in the reference pricelist item.
        """

        for p in self:
            if not p.reference_pricelist_id:
                continue

            if float_is_zero(p.ref_price, precision_rounding=p.reference_currency_id.rounding):
                prices = p.product_tmpl_id._convert_using_reference_currency(p.lst_price, inverse=True)
            else:
                prices = p.product_tmpl_id._convert_using_reference_currency(p.ref_price)

            if not p.ref_pricelist_item_id:
                attrs = p._get_product_attr_for_reference_price_list()
                attrs['pricelist_id'] = p.reference_pricelist_id.id
                attrs['fixed_price'] = prices['reference_price']
                item_id = p.env['product.pricelist.item'].create(attrs)
                p.ref_pricelist_item_id = item_id
            else:
                p.ref_pricelist_item_id.fixed_price = prices['reference_price']
            p.lst_price = prices['list_price']

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create method to ensure that the reference pricelist item is created
        when a product is created.
        """
        records = super().create(vals_list)
        records._inverse_ref_price()

        return records

    # @api.model_create_multi
    # def write(self, vals_list):
    #     """
    #     Override write method to ensure that the reference pricelist item is created
    #     when a product template is created.
    #     """
    #     records = super().write(vals_list)
    #     records._inverse_ref_price()

    #     return records
