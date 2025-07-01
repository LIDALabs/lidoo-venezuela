# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools import float_round


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
        compute='_compute_ref_pricelist_id',
        readonly=False,
        inverse='_inverse_ref_price',
        help="This is the reference price of the product in the reference pricelist. "
    )

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

    @api.depends('reference_pricelist_id')
    def _compute_ref_pricelist_id(self):
        """ Compute the reference pricelist for the product product."""
        PricelistItem = self.env['product.pricelist.item']
        Rate = self.env['res.currency.rate']
        pricelist = self.reference_pricelist_id
        if not pricelist:
            return

        today = fields.Date.today()
        for product in self:
            item_id = PricelistItem.search([
                ('pricelist_id', '=', pricelist.id),
                ('applied_on', '=', '0_product_variant'),
                ('compute_price', '=', 'fixed'),
                ('product_id', '=', product.id),
            ], limit=1)
            if item_id:
                reference_price = item_id.fixed_price if item_id else 0.0
            else:
                rate = Rate.compute_rate(pricelist.currency_id.id, today)['foreign_inverse_rate']
                reference_price = float_round(product.list_price * rate, pricelist.currency_id.decimal_places)

            product.ref_pricelist_item_id = item_id
            product.ref_price = reference_price

    @api.depends('reference_currency_id')
    def _inverse_ref_price(self):
        """
        Inverse method for ref_price field.
        This method updates the reference price in the reference pricelist item.
        """

        self.ensure_one()

        if self.ref_price == 0:
            return

        prices = self.product_tmpl_id._convert_to_reference_currency(self.ref_price)
        if not self.ref_pricelist_item_id:
            attrs = self._get_product_attr_for_reference_price_list()
            attrs['pricelist_id'] = self.reference_pricelist_id.id
            attrs['fixed_price'] = prices['reference_price']
            item_id = self.env['product.pricelist.item'].create(attrs)
            self.ref_pricelist_item_id = item_id
        else:
            self.ref_pricelist_item_id.fixed_price = prices['reference_price']
        self.lst_price = prices['list_price']
