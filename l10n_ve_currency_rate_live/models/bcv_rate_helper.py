from odoo import api, fields, models
from ...tools import binaural_bcv_query
import logging

_logger = logging.getLogger(__name__)


class BcvRateHelper(models.AbstractModel):
    _name = 'bcv.rate.helper'
    _description = 'BCV Rate Helper with Fallback'

    @api.model
    def _update_currency_rate(self, date, rate_usd, company_id):
        """Create or update the res.currency.rate entry for USD on the given date."""
        usd_currency = self.env.ref('base.USD', raise_if_not_found=False)
        if not usd_currency or not rate_usd:
            return
        Rate = self.env['res.currency.rate'].sudo()
        existing_rate = Rate.search([
            ('currency_id', '=', usd_currency.id),
            ('name', '=', date),
            ('company_id', '=', company_id)
        ], limit=1)
        vals = {
            'currency_id': usd_currency.id,
            'name': date,
            'inverse_company_rate': rate_usd,
            'company_id': company_id,
        }
        if existing_rate:
            existing_rate.write({'inverse_company_rate': rate_usd})
        else:
            Rate.create(vals)

    @api.model
    def get_bcv_rate_with_fallback(self, automatico=False):
        current_date = fields.Date.context_today(self)
        company_id = self.env.company.id

        # 1. Buscar tasa manual para la fecha/empresa actual
        manual_rate = self.env['bcv.rate.log'].search([
            ('rate_source', '=', 'manual'),
            ('date', '=', current_date),
            ('company_id', '=', company_id),
        ], order='created_at desc', limit=1)

        if manual_rate:
            self._update_currency_rate(manual_rate.date, manual_rate.rate_usd, company_id)
            return {
                'rates': {'USD': manual_rate.rate_usd},
                'date': manual_rate.date,
                'error': None,
                'used_fallback': False,
                'source': 'manual',
            }

        # 2. Consultar BCV
        result = binaural_bcv_query.get_bcv_rate_of_the_day(self)

        log_vals = {
            'date': current_date,
            'status': 'success' if not result.get('error') else 'error',
            'company_id': company_id,
        }

        used_fallback = False

        if result.get('error'):
            log_vals.update({
                'error_type': result['error'].get('type', 'Unknown'),
                'error_message': result['error'].get('message', ''),
            })

            last_success = self.env['bcv.rate.log'].search([
                ('status', '=', 'success'),
                ('company_id', '=', company_id)
            ], order='created_at desc', limit=1)

            if last_success:
                result['rates'] = {'USD': last_success.rate_usd}
                result['date'] = last_success.date
                used_fallback = True
                _logger.info(f"Using fallback rate: {last_success.rate_usd} from {last_success.date}")
            else:
                _logger.warning("No fallback rate available")
        else:
            log_vals['rate_usd'] = result['rates'].get('USD', 0.0)

        self.env['bcv.rate.log'].create(log_vals)

        result.setdefault('source', 'bcv')
        result['used_fallback'] = used_fallback
        return result
