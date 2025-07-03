# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tools import float_round


class ProductTemplate(models.Model):
    _inherit = "product.template"

    reference_pricelist_id = fields.Many2one(
        string="Lista de Precios Referenciales",
        comodel_name='product.pricelist',
        compute='_compute_reference_pricelist_id',
        store=True,
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

        return super().create(vals_list)

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
        Rate = self.env['res.currency.rate']
        pricelist = self.env.company.reference_pricelist_id
        if not pricelist:
            return

        today = fields.Date.today()
        for tmpl in self:
            item_id = PricelistItem.search([
                ('pricelist_id', '=', pricelist.id),
                ('applied_on', '=', '1_product'),
                ('compute_price', '=', 'fixed'),
                ('product_tmpl_id', '=', tmpl.id),
            ], limit=1)

            tmpl.reference_pricelist_id = pricelist
            tmpl.reference_pricelist_item_id = item_id
            if item_id:
                reference_price = item_id.fixed_price if item_id else 0.0
            else:
                rate = Rate.compute_rate(pricelist.currency_id.id, today)['foreign_inverse_rate']
                reference_price = float_round(tmpl.list_price * rate, pricelist.currency_id.decimal_places)

            tmpl.reference_price = reference_price

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

    def _convert_to_reference_currency(self, reference):
        """
        Convert the given price to the reference currency using the current rate.
        """
        Rate = self.env['res.currency.rate']
        today = fields.Date.today()
        rate = Rate.compute_rate(self.reference_currency_id.id, today)['foreign_rate']
        reference = float_round(reference, precision_rounding=self.reference_currency_id.rounding)
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

        self.ensure_one()

        if self.reference_price == 0:
            return

        prices = self._convert_to_reference_currency(self.reference_price)
        if not self.reference_pricelist_item_id:
            attrs = self._get_product_attr_for_reference_price_list()
            attrs['pricelist_id'] = self.reference_pricelist_id.id
            attrs['fixed_price'] = prices['reference_price']
            item_id = self.env['product.pricelist.item'].create(attrs)
            self.reference_pricelist_item_id = item_id
        else:
            self.reference_pricelist_item_id.fixed_price = prices['reference_price']
        self.list_price = prices['list_price']
