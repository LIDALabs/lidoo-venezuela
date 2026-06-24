from odoo import api, fields, models, _

class BcvRateWizard(models.TransientModel):
    _name = 'bcv.rate.wizard'
    _description = 'Wizard to consult BCV rate and update prices'

    name = fields.Char(string='Tasa del Día', readonly=True)
    rate_usd = fields.Float(string='Tasa BCV (USD)', digits=(12, 4), readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    date = fields.Datetime(string='Fecha Valor', readonly=True)
    used_fallback = fields.Boolean(string='Usó tasa anterior', readonly=True)
    error_message = fields.Text(string='Mensaje de error', readonly=True)
    info_message = fields.Text(string='Mensaje informativo', readonly=True)
    show_use_last_known_rate = fields.Boolean(string='Mostrar btn ultima tasa', default=False)

    @api.model
    def default_get(self, fields_list):
        res = super(BcvRateWizard, self).default_get(fields_list)
        
        # Self-healing menu parenting for Enterprise
        menu = self.env.ref('l10n_ve_currency_rate_live.menu_bcv_rate_wizard_account', raise_if_not_found=False)
        ent_menu = self.env.ref('account_accountant.menu_accounting', raise_if_not_found=False)
        if menu and ent_menu and menu.parent_id != ent_menu:
            menu.sudo().write({'parent_id': ent_menu.id})

        today = fields.Date.context_today(self)
        
        # 1. Buscar la tasa USD actualmente activa en el sistema
        usd_currency = self.env.ref('base.USD', raise_if_not_found=False)
        if usd_currency:
            active_rate = self.env['res.currency.rate'].search([
                ('currency_id', '=', usd_currency.id),
                ('company_id', '=', self.env.company.id),
            ], order='name desc', limit=1)
            
            if active_rate:
                rate_value = active_rate.inverse_company_rate or (
                    1.0 / active_rate.rate if active_rate.rate else 0.0
                )
                rate_date = active_rate.name.date() if hasattr(active_rate.name, 'date') else active_rate.name
                
                res.update({
                    'rate_usd': rate_value,
                    'date': fields.Datetime.to_datetime(rate_date),
                    'name': f"Tasa del {rate_date}",
                    'used_fallback': False,
                    'error_message': '',
                    'show_use_last_known_rate': False,
                })
                
                # Si la tasa activa es de hoy, no mostrar boton
                if rate_date >= today:
                    return res
                
                # Si la tasa activa es anterior a hoy, mostrar boton para consultar BCV
                res['show_use_last_known_rate'] = True
                res['info_message'] = (
                    f"La tasa activa es del {rate_date}. "
                    "Puede consultar el BCV para obtener la tasa actualizada."
                )
                return res
        
        # 2. No hay tasa activa — consultar BCV directamente
        res['show_use_last_known_rate'] = True
        res['info_message'] = (
            "No se encontró una tasa USD en el sistema. "
            "Consulte el BCV para obtener la tasa."
        )
        try:
            helper = self.env['bcv.rate.helper']
            result = helper.get_bcv_rate_with_fallback(automatico=False)
            if result.get('rates') and result.get('date'):
                rate_date = result['date']
                res.update({
                    'rate_usd': result['rates'].get('USD', 0.0),
                    'date': fields.Datetime.now(),
                    'name': f"Tasa BCV del {rate_date}",
                    'used_fallback': result.get('used_fallback', False),
                    'error_message': result.get('error', {}).get('message', '') if result.get('error') else '',
                })
        except Exception:
            pass
        return res

    def action_get_bcv_rate(self):
        """Consultar tasa del BCV."""
        self.ensure_one()
        helper = self.env['bcv.rate.helper']
        result = helper.get_bcv_rate_with_fallback(automatico=False)
        
        if result.get('rates') and result.get('date'):
            today = fields.Date.context_today(self)
            rate_date = result['date']
            show_btn = rate_date > today
            info_msg = ''
            if show_btn:
                info_msg = (
                    f"El BCV publicó una tasa con Fecha Valor {rate_date}, "
                    "que es un día futuro. Esto ocurre en fines de semana "
                    "y feriados. Puede cargar la última tasa conocida."
                )
            self.write({
                'rate_usd': result['rates'].get('USD', 0.0),
                'date': fields.Datetime.now(),
                'name': f"Tasa BCV del {rate_date}",
                'used_fallback': result.get('used_fallback', False),
                'error_message': result.get('error', {}).get('message', '') if result.get('error') else '',
                'info_message': info_msg,
                'show_use_last_known_rate': show_btn,
            })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bcv.rate.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_use_last_known_rate(self):
        """Cargar la ultima tasa conocida antes de hoy desde la base de datos.
        Util para dias feriados cuando el BCV publica una tasa con Fecha Valor
        futura y se necesita usar la ultima tasa real del dia anterior."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        
        usd_currency = self.env.ref('base.USD', raise_if_not_found=False)
        if not usd_currency:
            self.write({
                'info_message': 'No se encontro la moneda USD en el sistema.',
            })
            return self._reopen()
        
        # Buscar la ultima tasa USD guardada ANTES de hoy
        last_rate = self.env['res.currency.rate'].search([
            ('currency_id', '=', usd_currency.id),
            ('company_id', '=', self.env.company.id),
            ('name', '<', today),
        ], order='name desc', limit=1)
        
        if not last_rate:
            self.write({
                'rate_usd': 0.0,
                'name': 'Sin tasa anterior',
                'info_message': (
                    'No se encontro ninguna tasa USD guardada antes de hoy '
                    f'({today}). Consulte el BCV o ingrese la tasa manualmente.'
                ),
            })
            return self._reopen()
        
        # inverse_company_rate es la tasa legible (ej: 621.53)
        # rate es el inverso (1/621.53 ≈ 0.0016)
        rate_value = last_rate.inverse_company_rate or (
            1.0 / last_rate.rate if last_rate.rate else 0.0
        )
        rate_date = last_rate.name.date() if hasattr(last_rate.name, 'date') else last_rate.name
        
        self.write({
            'rate_usd': rate_value,
            'date': fields.Datetime.to_datetime(rate_date),
            'name': f"Tasa del {rate_date}",
            'used_fallback': False,
            'error_message': '',
            'show_use_last_known_rate': False,
            'info_message': (
                f"Se cargo la ultima tasa conocida del {rate_date} "
                f"({rate_value} Bs/USD). Puede usar esta tasa para "
                "actualizar precios si hoy es dia no laborable."
            ),
        })
        return self._reopen()

    def _reopen(self):
        """Reabrir el wizard con los datos actualizados."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bcv.rate.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_view_history(self):
        """Open BCV rate history log"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Historial BCV',
            'res_model': 'bcv.rate.log',
            'view_mode': 'tree,form',
            'target': 'current',
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

        # 1. Obtener la fecha de la tasa (puede ser hoy o una fecha anterior)
        rate_date = self.date.date() if hasattr(self.date, 'date') else self.date
        
        # 2. Asegurar que la tasa este guardada en la base de datos (USD)
        usd_currency = self.env.ref('base.USD', raise_if_not_found=False)
        if usd_currency:
            Rate = self.env['res.currency.rate']
            existing_rate = Rate.search([
                ('currency_id', '=', usd_currency.id),
                ('name', '=', rate_date),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            
            vals = {
                'currency_id': usd_currency.id,
                'name': rate_date,
                'inverse_company_rate': self.rate_usd,
                'company_id': self.company_id.id,
            }
            if existing_rate:
                existing_rate.write({'inverse_company_rate': self.rate_usd})
            else:
                Rate.create(vals)

        # 3. Registrar en el log historial con todos los detalles
        log_vals = {
            'date': rate_date,
            'rate_usd': self.rate_usd,
            'status': 'success',
            'company_id': self.company_id.id,
            'automatico': False,
            'description': (
                f"Actualización manual de precios desde el wizard. "
                f"Tasa aplicada: {self.rate_usd} Bs/USD con Fecha Valor {rate_date}. "
                f"Los precios de productos fueron actualizados con esta tasa."
            ),
        }
        self.env['bcv.rate.log'].create(log_vals)

        # 4. Proceder con el comando de actualizacion de precios
        pricelist_obj = self.env['product.pricelist']
        if hasattr(pricelist_obj, '_update_product_prices'):
             pricelist_obj._update_product_prices()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Exito'),
                'message': _('Los precios han sido actualizados con la tasa del %s (%.4f Bs/USD)') % (rate_date, self.rate_usd),
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
