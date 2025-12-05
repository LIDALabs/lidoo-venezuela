import logging
import json

from odoo import http, fields
from odoo.http import request, route
from odoo.fields import Command

_logger = logging.getLogger(__name__)

class RegisterInvoiceController(http.Controller):
    """
    Estructura del JSON
    {
        "rif": "30292222",
        "payment_reference": "F16TRACK",
        "lines": [
            {"sku": "TRA", "quantity": 3, "price_unit": 11.0},
            {"sku": "AQUA", "quantity": 2, "price_unit": 4.0}
        ]
    }
    """
    @route('/api/invoice', type='http', auth='public', methods=['POST'], csrf=False)
    def register_invoice(self, **kw):

        data = { }
        try: 
            raw_data = request.httprequest.data
            if not raw_data: 
                return self._response({'satus': 'error', 'message': 'empty body'}, 400)
            try:
                data = json.loads(raw_data)
            except ValueError:
                return self._response({'satus': 'error', 'message': 'JSON invalid'}, 400)
                ...
            # var catch
            vat = data.get('rif')
            lines = data.get('lines')
            payment_reference = data.get('payment_reference')
            company_id  = request.env.company.id

            # validation for vat
            if not vat:
                ...
            Contact = request.env['res.partner']
            contact = Contact.sudo().search([('vat', '=', vat)], limit=1, offset=0)

            # validation cuando no se encuentra el cliente o contacto
            if not contact:
                ...
             
            Product = request.env['product.product']
            invoice_lines = []

            for line in lines:
                sku = line.get('sku')

                # validation
                if not sku:
                    ...

                product = Product.sudo().search([('default_code', '=', sku)], limit=1, offset=0)

                price_unit = line.get('price_unit', product.lst_price) # <--- Validation por aqui Igues
                
                invoice_lines.append(Command.create({
                    'product_id': product.id,
                    'quantity': line.get('quantity', 1),
                    'price_unit': price_unit
                }))

                AccountMove = request.env['account.move']

                invoice = AccountMove.sudo().create({
                    'move_type': 'out_invoice',
                    'partner_id': contact.id,
                    'invoice_date': fields.Date.today(),
                    'company_id': company_id,
                    'payment_reference': payment_reference,
                    'ref': payment_reference,
                    'invoice_line_ids': invoice_lines
                })

                invoice._onchange_partener_id()
                invoice._compute_amount()

                if len(invoice.line_ids) < 2:
                    return self._response({'status': 'error', 'message': 'El cliente no tiene cuenta contable configurada'}, 400)

                return self._response({
                    'status': 'success',
                    'invoice': invoice,
                    'message': 'factura creada'
                })

        except Exception as e: 
            _logger.exception('Error en API HTTP')
            return self._response({'status': 'error', 'message': str(e)}, 500)
            ...
        ...

    def _response(self, data, status=200):
        # * Helper para dar una respuesta JSON para el type='http'
        return request.make_response(
            json.dumps(data),
            headers = [('Content-Type', 'application/json')],
            status=status
        )