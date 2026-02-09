
from odoo import fields, api, models, _
from odoo.tools.float_utils import float_round
from dateutil.relativedelta import relativedelta

class NetAmountWizard(models.TransientModel): 
    _name = "net.amount.wizard"
    _description = "Asistente de reportes de las cantidades netas"
  
    # ------------------------------    
    # Valores por defectos de las fechas
    # Son los ultioms 30 dias
    def _get_default_date_from(self):
        # ultimos 30 dias
        return ( fields.Datetime.now() - relativedelta(months=1) )
        ...

    def _get_defualt_date_to(self): 
        # dia de hoy
        return fields.Datetime.now()
        ...
    # ------------------------------
        
    product_id = fields.Many2one(
        'product.product',
        "Producto",
        required=True,
    )

    date_from = fields.Date('Desde', default=_get_default_date_from, required=True)
    date_to = fields.Date('Hasta', default=_get_defualt_date_to, required=True)


    def action_sent_result(self): 
        self.ensure_one()

        return {
            'name': 'Reporte de Movimiento',
            'type': 'ir.actions.act_window',
            'res_model': 'net.amount.result',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_product_id': self.product_id.id,
                'default_date_from': self.date_from,
                'default_date_to': self.date_to,
            }
        }
    ...

