from odoo import api, fields, models, _
from ...tools import binaural_bcv_query

class BcvRateWizard(models.TransientModel):
    _name = 'bcv.rate.wizard'
    _description = 'Wizard to consult BCV rate and update prices'

    name = fields.Char(string='Tasa del Día', readonly=True)
    rate_usd = fields.Float(string='Tasa BCV (USD)', digits=(12, 4), readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    date = fields.Date(string='Fecha de Tasa', readonly=True)

    def action_get_bcv_rate(self):
        self.ensure_one()
        rates, rate_day = binaural_bcv_query.get_bcv_rate_of_the_day(self)
        if rate_day:
            self.write({
                'rate_usd': rates.get('USD', 0.0),
                'date': rate_day,
                'name': f"Tasa BCV del {rate_day}"
            })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bcv.rate.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_update_prices(self):
        self.ensure_one()
        pricelist_obj = self.env['product.pricelist']
        if hasattr(pricelist_obj, '_update_product_prices'):
             pricelist_obj._update_product_prices()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Éxito'),
                'message': _('Los precios han sido actualizados con la tasa consultada'),
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
