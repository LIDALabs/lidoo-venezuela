import datetime

from dateutil.relativedelta import relativedelta
from odoo import SUPERUSER_ID, api

from . import models


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
