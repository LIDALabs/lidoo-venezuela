# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tools import float_round


class Pricelist(models.Model):
    _inherit = "product.pricelist"

    is_reference_price = fields.Boolean(
        string="Es la lista de Precios Referencial",
        computed='_compute_is_reference_price',
        # store=True,
        readonly=True,
        default=False
    )

    def _compute_is_reference_price(self):
        for pl in self:
            pl.is_reference_price = pl.id == pl.company_id.reference_pricelist_id.id

    def action_update_product_prices(self):
        if not self._update_product_prices():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('La empresa no tiene una lisa de precios referenciales asociada'),
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Los precios han sido actualizados'),
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_fill_reference_pricelist(self):
        ref_pricelist = self.env.company.reference_pricelist_id
        if not ref_pricelist:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('La empresa no tiene una lisa de precios referenciales asociada'),
                    'sticky': True,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

        Rate = self.env['res.currency.rate']
        today = fields.Date.today()
        rate = Rate.compute_rate(ref_pricelist.currency_id.id, today)['foreign_inverse_rate']

        items = []
        # product_tmpls = self.env['product.product'].search([
        #     '&', ('company_id', '=', self.env.company.id), ('active', '=', True)])
        # for p in product_tmpls:
        #     items.append({
        #         'pricelist_id': ref_pricelist.id,
        #         'applied_on': '1_product',
        #         'categ_id': False,
        #         'product_tmpl_id': p.id,
        #         'product_id': False,
        #         'base': 'list_price',
        #         'compute_price': 'fixed',
        #         'fixed_price': float_round(p.list_price * rate, ref_pricelist.currency_id.decimal_places)
        #     })

        products = self.env['product.product'].search([
            '&', ('sale_ok', '=', True), ('active', '=', True)])
        for p in products:
            items.append({
                'pricelist_id': ref_pricelist.id,
                'applied_on': '0_product_variant',
                'categ_id': False,
                'product_tmpl_id': p.product_tmpl_id.id,
                'product_id': p.id,
                'base': 'list_price',
                'compute_price': 'fixed',
                'fixed_price': float_round(p.lst_price * rate, ref_pricelist.currency_id.decimal_places)
            })

        item_vals = [Command.clear()]
        item_vals += [Command.create(item) for item in items]
        ref_pricelist.write({
            'item_ids': item_vals
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('La lista de precios referenciales ha sido generada'),
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def _update_product_prices(self):
        ref_pricelist = self.env.company.reference_pricelist_id
        if not ref_pricelist:
            return False

        Rate = self.env['res.currency.rate']
        today = fields.Date.today()
        rate = Rate.compute_rate(ref_pricelist.currency_id.id, today)['foreign_rate']

        item_ids = self.item_ids
        prices_for_variants = item_ids.filtered(lambda p: not p.product_tmpl_id)
        for price in (item_ids - prices_for_variants):
            price.product_tmpl_id.list_price = float_round(price.fixed_price * rate, self.env.company.currency_id.decimal_places)
        for price in prices_for_variants:
            price.product_id.lst_price = float_round(price.fixed_price * rate, self.env.company.currency_id.decimal_places)

        return True
