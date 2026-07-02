from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class BcvRateLog(models.Model):
    _name = 'bcv.rate.log'
    _description = 'BCV Rate Query Log'
    _order = 'created_at desc'

    date = fields.Date('Fecha de consulta', required=True)
    rate_usd = fields.Float('Tasa USD', digits=(12, 4))
    rate_source = fields.Selection([
        ('bcv', 'BCV'),
        ('manual', 'Manual')
    ], string='Fuente de tasa', default='bcv', required=True)
    manual_rate_creator_id = fields.Many2one(
        'res.users',
        string='Creado por (manual)',
        readonly=True,
    )
    status = fields.Selection([
        ('success', 'Exitosa'),
        ('error', 'Error')
    ], string='Estado', required=True)
    error_type = fields.Char('Tipo de error')
    error_message = fields.Text('Mensaje de error')
    created_at = fields.Datetime('Fecha de creación', default=fields.Datetime.now, readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)

    automatico = fields.Boolean(
        'Automático', 
        default=False,
        help='Indica si la consulta fue realizada automáticamente por el cron (True) o manualmente desde el wizard (False).'
    )

    @api.model_create_multi
    def create(self, vals_list):
        manual_group = 'l10n_ve_currency_rate_live.group_bcv_manual_rate'
        for vals in vals_list:
            if vals.get('rate_source') == 'manual':
                if not self.env.user.has_group(manual_group):
                    raise AccessError(_("Solo el usuario root puede crear tasas manuales."))
                vals['manual_rate_creator_id'] = self.env.user.id
                vals.setdefault('status', 'success')
        return super(BcvRateLog, self).create(vals_list)

    def write(self, vals):
        if 'rate_source' in vals:
            manual_group = 'l10n_ve_currency_rate_live.group_bcv_manual_rate'
            can_change_source = self.env.user.has_group(manual_group)
            for log in self:
                old_source = log.rate_source
                new_source = vals.get('rate_source')
                if old_source != new_source and (old_source == 'manual' or new_source == 'manual'):
                    if not can_change_source:
                        raise AccessError(_("Solo el usuario root puede cambiar la fuente de tasa a/desde manual."))
        return super(BcvRateLog, self).write(vals)
