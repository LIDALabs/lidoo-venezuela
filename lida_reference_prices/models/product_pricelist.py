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
        compute='_compute_is_reference_price',
        # store=True,
        # readonly=True,
        default=False
    )

    @api.depends('company_id.reference_pricelist_id')
    def _compute_is_reference_price(self):
        for pl in self:
            pl.is_reference_price = pl.id == pl.company_id.reference_pricelist_id.id

    def action_change_reference_pricelist(self):
        """ Set this pricelist as the reference pricelist for the company. """
        self.ensure_one()

        if self.is_reference_price:
            raise UserError(_("Esta lista de precios ya es la referencial."))

        if self.currency_id == self.env.company.currency_id:
            raise UserError(_("La lista de precios referencial debe tener una moneda diferente a la de la empresa."))

        self.env.company.reference_pricelist_id = self.id

        self.env['product.template'].write({
            'reference_pricelist_id': self.id,
            'reference_currency_id': self.currency_id.id,
        })

        self.action_fill_reference_pricelist()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('La lista de precios ha sido establecida como referencial'),
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

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
        pricelist = self.env.company.reference_pricelist_id
        if not pricelist:
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
        rate = Rate.compute_rate(pricelist.currency_id.id, today)['foreign_inverse_rate']

        items = []
        product_tmpls = self.env['product.template'].search([
            '&', ('sale_ok', '=', True), ('active', '=', True)])
        # prefetch variants to avoid N+1 queries
        product_tmpls.product_variant_ids
        for tmpl in product_tmpls:
            attrs = tmpl._get_product_attr_for_reference_price_list()
            attrs['pricelist_id'] = pricelist.id
            attrs['fixed_price'] = float_round(tmpl.list_price * rate, pricelist.currency_id.decimal_places)
            items.append(attrs)

            for p in tmpl.product_variant_ids:
                attrs = p._get_product_attr_for_reference_price_list()
                attrs['pricelist_id'] = pricelist.id
                attrs['fixed_price'] = float_round(p.lst_price * rate, pricelist.currency_id.decimal_places)
                items.append(attrs)

        # products = self.env['product.product'].search([
        #     '&', ('sale_ok', '=', True), ('active', '=', True)])

        item_vals = [Command.clear()]
        item_vals += [Command.create(item) for item in items]
        pricelist.write({
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
