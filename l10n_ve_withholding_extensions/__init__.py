from odoo import SUPERUSER_ID, api

from . import models


def setup_accounts(env):
    env = api.Environment(env.cr, SUPERUSER_ID, {})

    if env.company.chart_template != 've_lida':
        return

    AccountChartTemplate = env['account.chart.template']

    vals = {}
    if not env.company.iva_supplier_retention_journal_id:
        acc = AccountChartTemplate.ref('lida_withholding_iva_suppliers', raise_if_not_found=False)
        vals['iva_supplier_retention_journal_id'] = acc and acc.id
    if not env.company.iva_customer_retention_journal_id:
        acc = AccountChartTemplate.ref('lida_withholding_iva_customers', raise_if_not_found=False)
        vals['iva_customer_retention_journal_id'] = acc and acc.id
    if not env.company.islr_supplier_retention_journal_id:
        acc = AccountChartTemplate.ref('lida_withholding_islr_suppliers', raise_if_not_found=False)
        vals['islr_supplier_retention_journal_id'] = acc and acc.id
    if not env.company.islr_customer_retention_journal_id:
        acc = AccountChartTemplate.ref('lida_withholding_islr_customers', raise_if_not_found=False)
        vals['islr_customer_retention_journal_id'] = acc and acc.id

    env.company.write(vals)
    return
