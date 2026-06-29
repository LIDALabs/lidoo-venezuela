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
                _logger.info(f"[{company.name}] BCV: Fin de semana. No se actualiza la tasa.")
                return
            
            helper = self.env['bcv.rate.helper']
            result = helper.get_bcv_rate_with_fallback(automatico=True)
            
            if not result.get('rates') or not result.get('date'):
                _logger.warning(f"[{company.name}] BCV: No se pudo obtener la tasa. Sin datos de respaldo.")
                return
            
            rate_day = result['date']
            rates = result['rates']
            
            if not rate_day:
                _logger.info(f"[{company.name}] BCV: No se recibio fecha de valor.")
                return
            
            # If 'Fecha Valor' is in the future, the BCV published a rate for a
            # date that has not arrived yet.  This typically happens on holidays:
            # the BCV pre-publishes the next business day's rate, but the company
            # does not work today so it should keep using yesterday's rate.
            if rate_day > current_date:
                _logger.info(
                    f"[{company.name}] BCV: La fecha de valor ({rate_day}) es posterior "
                    f"a la fecha actual ({current_date}). Se mantiene la ultima tasa "
                    f"conocida. No se genera un nuevo registro de tasa."
                )
                return
            
            veb_per_usd = rates["USD"]
            
            # Additional safety: if the rate is identical to the last known one,
            # skip to avoid creating a duplicate entry.
            usd_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
            if usd_currency:
                last_rate = self.env['res.currency.rate'].search([
                    ('currency_id', '=', usd_currency.id),
                    ('company_id', '=', company.id),
                ], order='name desc', limit=1)
                
                # inverse_company_rate is the readable rate (e.g. 621.53)
                last_rate_value = last_rate.inverse_company_rate if last_rate else 0.0
                if last_rate and abs(last_rate_value - veb_per_usd) < 0.0001:
                    _logger.info(
                        f"[{company.name}] BCV: La tasa no cambio ({veb_per_usd}). "
                        f"No se genera un nuevo registro."
                    )
                    return
            
            data = {}
            for c, rate in rates.items():
                data[c] = (veb_per_usd/rate, rate_day)
            data["USD"] = (1, rate_day)
            data["VEF"] = (veb_per_usd, rate_day)
            
            if result.get('used_fallback'):
                _logger.info(f"[{company.name}] BCV: Usando tasa de respaldo: {veb_per_usd}")
            else:
                _logger.info(f"[{company.name}] BCV: Tasa actualizada correctamente: {veb_per_usd}")
            
            return data