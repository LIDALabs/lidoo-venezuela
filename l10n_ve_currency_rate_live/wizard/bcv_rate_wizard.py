from odoo import api, fields, models, _
from ...tools import binaural_bcv_query

class BcvRateWizard(models.TransientModel):
    _name = 'bcv.rate.wizard'
    _description = 'Wizard to consult BCV rate and update prices'

    name = fields.Char(string='Tasa del Día', readonly=True)
    rate_usd = fields.Float(string='Tasa BCV (USD)', digits=(12, 4), readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    date = fields.Date(string='Fecha de Tasa', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super(BcvRateWizard, self).default_get(fields_list)
        
        # Self-healing menu parenting for Enterprise
        # This runs on every wizard open to ensure compatibility even if post_init didn't run
        menu = self.env.ref('l10n_ve_currency_rate_live.menu_bcv_rate_wizard_account', raise_if_not_found=False)
        ent_menu = self.env.ref('account_accountant.menu_accounting', raise_if_not_found=False)
        if menu and ent_menu and menu.parent_id != ent_menu:
            menu.sudo().write({'parent_id': ent_menu.id})

        try:
            rates, rate_day = binaural_bcv_query.get_bcv_rate_of_the_day(self)
            if rate_day:
                res.update({
                    'rate_usd': rates.get('USD', 0.0),
                    'date': rate_day,
                    'name': f"Tasa BCV del {rate_day}"
                })
        except Exception:
            pass
        return res

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
        if not self.rate_usd or not self.date:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Aviso'),
                    'message': _('Debe consultar la tasa antes de actualizar.'),
                    'sticky': False,
                }
            }

        # 1. Asegurar que la tasa esté guardada en la base de datos (USD)
        usd_currency = self.env.ref('base.USD', raise_if_not_found=False)
        if usd_currency:
            Rate = self.env['res.currency.rate']
            existing_rate = Rate.search([
                ('currency_id', '=', usd_currency.id),
                ('name', '=', self.date),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            
            # Según l10n_ve_rate, inverse_company_rate es la tasa legible (e.g. 50.0)
            # Al escribir inverse_company_rate, Odoo calcula company_rate y rate.
            vals = {
                'currency_id': usd_currency.id,
                'name': self.date,
                'inverse_company_rate': self.rate_usd,
                'company_id': self.company_id.id,
            }
            if existing_rate:
                existing_rate.write({'inverse_company_rate': self.rate_usd})
            else:
                Rate.create(vals)

        # 2. Proceder con el comando de actualización de precios
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