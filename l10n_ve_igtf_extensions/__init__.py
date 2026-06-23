# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

from . import models, wizard


def setup_accounts(env):
    env = api.Environment(env.cr, SUPERUSER_ID, {})

    journals = env['account.journal'].search([('type', "in", ['cash', 'bank']), ('currency_id.name', "not like", "VE")])

    if journals:
        journals.write({'is_igtf': True})
    return
