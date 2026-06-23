from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

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
                _logger.info(f"Skipping BCV update for {company.name}: not a business day")
                return
            
            helper = self.env['bcv.rate.helper']
            result = helper.get_bcv_rate_with_fallback()
            
            if not result.get('rates') or not result.get('date'):
                _logger.warning(f"BCV rate query failed for {company.name}, no fallback available")
                return
            
            rate_day = result['date']
            rates = result['rates']
            
            is_valid_update_date = str(rate_day) == str(current_date)
            if not rate_day or not is_valid_update_date:
                _logger.info(f"BCV rate date {rate_day} doesn't match current date {current_date}")
                return
            
            veb_per_usd = rates["USD"]
            data = {}
            for c, rate in rates.items():
                data[c] = (veb_per_usd/rate, rate_day)
            data["USD"] = (1, rate_day)
            data["VEF"] = (veb_per_usd, rate_day)
            
            if result.get('used_fallback'):
                _logger.info(f"Using fallback BCV rate for {company.name}: {veb_per_usd}")
            else:
                _logger.info(f"Successfully updated BCV rate for {company.name}: {veb_per_usd}")
            
            return data