import datetime

from dateutil.relativedelta import relativedelta
from odoo import SUPERUSER_ID, api

from . import models
from . import wizard


def _post_init_hook(env):
    # Fix menu parenting for Enterprise (Contabilidad)
    menu = env.ref('l10n_ve_currency_rate_live.menu_bcv_rate_wizard_account', raise_if_not_found=False)
    ent_menu = env.ref('account_accountant.menu_accounting', raise_if_not_found=False)
    if menu and ent_menu:
        menu.parent_id = ent_menu
    
    # Existing setup logic
    setup_currency_update(env)

def setup_currency_update(env):
    env = api.Environment(env.cr, SUPERUSER_ID, {})

    env.company.write({
        "currency_provider": "bcv",
        "currency_interval_unit": "daily",
        "currency_next_execution_date": datetime.date.today() + relativedelta(days=+1)
    })

    try:
        env.company.update_currency_rates()
    except Exception:
        pass
    return
