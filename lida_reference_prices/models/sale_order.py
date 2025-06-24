# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.exceptions import UserError
from odoo.fields import Command


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def cron_action_update_prices(self):
        for sale in self.search([('state', 'in', ['draft', 'sent', 'sale']), ('locked', '=', False)]):
            sale._recompute_prices()
