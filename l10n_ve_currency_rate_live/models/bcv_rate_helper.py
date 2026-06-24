from odoo import api, fields, models
from ...tools import binaural_bcv_query
import logging

_logger = logging.getLogger(__name__)


class BcvRateHelper(models.AbstractModel):
    _name = 'bcv.rate.helper'
    _description = 'BCV Rate Helper with Fallback'

    @api.model
    def get_bcv_rate_with_fallback(self, automatico=False):
        """
        Consulta la tasa del BCV con logging y fallback automático.

        Args:
            automatico (bool): True si la consulta fue iniciada por el cron,
                               False si fue iniciada manualmente desde el wizard.

        Returns:
            dict: {
                'rates': {'USD': float, 'EUR': float, ...},
                'date': date object,
                'error': None or {'type': str, 'message': str},
                'used_fallback': bool
            }
        """
        result = binaural_bcv_query.get_bcv_rate_of_the_day(self)
        current_date = fields.Date.context_today(self)
        origen = "automático (cron)" if automatico else "manual (wizard)"

        log_vals = {
            'date': current_date,
            'status': 'success' if not result.get('error') else 'error',
            'company_id': self.env.company.id,
            'automatico': automatico,
        }
        
        used_fallback = False
        
        if result.get('error'):
            # Loguear el error
            error_type = result['error'].get('type', 'Unknown')
            error_msg = result['error'].get('message', '')
            log_vals.update({
                'error_type': error_type,
                'error_message': error_msg,
            })
            
            # Buscar última tasa exitosa como fallback
            last_success = self.env['bcv.rate.log'].search([
                ('status', '=', 'success'),
                ('company_id', '=', self.env.company.id)
            ], order='created_at desc', limit=1)
            
            if last_success:
                result['rates'] = {'USD': last_success.rate_usd}
                result['date'] = last_success.date
                used_fallback = True
                log_vals['rate_usd'] = last_success.rate_usd
                log_vals['description'] = (
                    f"Consulta {origen} al BCV falló ({error_type}: {error_msg}). "
                    f"Se usó como respaldo la última tasa exitosa: "
                    f"{last_success.rate_usd} Bs/USD con Fecha Valor {last_success.date}."
                )
                _logger.info(f"Using fallback rate: {last_success.rate_usd} from {last_success.date}")
            else:
                log_vals['description'] = (
                    f"Consulta {origen} al BCV falló ({error_type}: {error_msg}). "
                    f"No hay tasa de respaldo disponible en el sistema."
                )
                _logger.warning("No fallback rate available")
        else:
            # Consulta exitosa
            rate_usd = result['rates'].get('USD', 0.0)
            rate_date = result.get('date', current_date)
            log_vals['rate_usd'] = rate_usd
            log_vals['date'] = rate_date
            log_vals['description'] = (
                f"Consulta {origen} al BCV exitosa. "
                f"Tasa USD: {rate_usd} Bs/USD con Fecha Valor {rate_date}."
            )
        
        # Crear el log
        self.env['bcv.rate.log'].create(log_vals)
        
        result['used_fallback'] = used_fallback
        return result
