
from odoo import fields, api, models, _
from odoo.tools.float_utils import float_round

class NetAmountWizard(models.TransientModel): 
    _name = "net.amount.wizard"
    _description = "Asistente de reportes de las cantidades netas"

    product_id = fields.Many2one(
        'product.product',
        "Producto",
        required=True,
    )

    date_from = fields.Date('Desde', required=True)
    date_to = fields.Date('Hasta', required=True)


    def action_sent_result(self): 
        self.ensure_one()

        return {
            'name': 'Reporte de Movimiento',
            'type': 'ir.actions.act_window',
            'res_model': 'net.amount.result',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_id': self.product_id.id,
                'default_date_from': self.date_from,
                'default_date_to': self.date_to,
            }
        }
    ...

