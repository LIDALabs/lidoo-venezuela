from odoo import api, fields, models, _
from ...tools import binaural_bcv_query

class ResCompany(models.Model):
    _inherit = "res.company"

    currency_provider = fields.Selection(
        selection_add=[("bcv", "Venezuelan Central Bank")]
    )

    can_update_habil_days = fields.Boolean(default=True)

    @api.model
    def _parse_bcv_data(self, availible_currencies):
        companies = self.env['res.company'].search([])
        for company in companies:
            can_update_habil_days = company.can_update_habil_days
            current_date = fields.Date.context_today(self)
            day = current_date.isoweekday()
            is_habil_day = day <= 5
            invalid_update_in_habil_day = not is_habil_day and can_update_habil_days
            if invalid_update_in_habil_day:
                return
            rates, rate_day = binaural_bcv_query.get_bcv_rate_of_the_day(self)
            is_valid_update_date = str(rate_day) == str(current_date)
            if not rate_day or not is_valid_update_date:
                return
            
            veb_per_usd = rates["USD"]
            data = {}
            for c, rate in rates.items():
                data[c] = (veb_per_usd/rate, rate_day)
            data["USD"] = (1, rate_day)
            data["VEF"] = (veb_per_usd, rate_day)
            return data