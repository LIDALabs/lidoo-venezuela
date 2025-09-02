# -*- coding: utf-8 -*-

from . import models
from . import wizard


# def assign_correlative_sequence(env):
#     env = api.Environment(env.cr, SUPERUSER_ID, {})
#     correlative_sequence = env.ref('l10n_ve_invoice.invoice_correlative', raise_if_not_found=False)
#     if not correlative_sequence:
#         return
#     sale_journals = env["account.journal"].with_context(active_test=False).search([('type', '=', 'sale')])
#     if sale_journals:
#         sale_journals.write({'series_correlative_sequence_id': correlative_sequence.id})
#     return
