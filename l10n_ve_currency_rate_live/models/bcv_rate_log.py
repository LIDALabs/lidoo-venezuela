from odoo import api, fields, models


class BcvRateLog(models.Model):
    _name = 'bcv.rate.log'
    _description = 'BCV Rate Query Log'
    _order = 'created_at desc'

    date = fields.Date('Fecha de consulta', required=True)
    rate_usd = fields.Float('Tasa USD', digits=(12, 4))
    status = fields.Selection([
        ('success', 'Exitosa'),
        ('error', 'Error')
    ], string='Estado', required=True)
    error_type = fields.Char('Tipo de error')
    error_message = fields.Text('Mensaje de error')
    created_at = fields.Datetime('Fecha de creación', default=fields.Datetime.now, readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', default=lambda self: self.env.company)
    automatico = fields.Boolean('Automático', default=False, help='Indica si la consulta fue realizada automáticamente por el cron (True) o manualmente desde el wizard (False).')
