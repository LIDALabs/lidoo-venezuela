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

        data = {}
        try:
            raw_data = request.httprequest.data
            if not raw_data:
                return self._response({'satus': 'error', 'message': 'empty body'}, 400)
            try:
                data = json.loads(raw_data)
            except ValueError:
                return self._response({'satus': 'error', 'message': 'JSON invalid'}, 400)
            # var catch
            vat = data.get('rif')
            lines = data.get('lines')
            payment_reference = data.get('payment_reference')
            company_id = request.env.company.id

            # validation for vat
            if not vat:
                return self._response({'status': 'error', 'message': 'Falta el RIF'}, 400)
            Contact = request.env['res.partner']
            clean_vat = str(vat).strip().upper().replace(' ', '')
            possible_vats = [clean_vat]
            if '-' in clean_vat:
                possible_vats.append(clean_vat.replace('-', ''))
            elif clean_vat[0] in ['V', 'J', 'E', 'G', 'P'] and clean_vat[1:].isdigit():
                possible_vats.append(f"{clean_vat[0]}-{clean_vat[1:]}")
            elif clean_vat.isdigit():
                possible_vats.extend([
                    f'V-{clean_vat}', f'V{clean_vat}',
                    f'J-{clean_vat}', f'J{clean_vat}',
                    f'E-{clean_vat}', f'G-{clean_vat}'
                ])
            contact = Contact.sudo().search([('vat', 'in', possible_vats)], limit=1, offset=0)

            Product = request.env['product.product']
            invoice_lines = []

            for line in lines:
                sku = line.get('sku')

                if not sku:
                    return self._response({'status': 'error', 'message': 'Falta SKU en una línea'}, 400)

                product = Product.sudo().search([('default_code', '=', sku)], limit=1)

                if not product:
                    return self._response({'status': 'error', 'message': f'Producto no encontrado: {sku}'}, 400)

                if 'price_unit' in line and 'price_total' in line:
                    return self._response({
                        'status': 'error',
                        'message': f'Ambigüedad en producto {sku}: No puedes enviar "price_unit" y "price_total" al mismo tiempo.'
                    }, 400)
                # ----------------------------------

                qty = float(line.get('quantity', 1))
                price_unit = 0.0

                # Lógica de cálculo de precio
                if 'price_unit' in line:
                    price_unit = float(line.get('price_unit'))

                elif 'price_total' in line:
                    if qty == 0:
                        return self._response({'status': 'error', 'message': 'Cantidad no puede ser 0 si usas precio total'}, 400)
                    price_total = float(line.get('price_total'))
                    price_unit = price_total / qty

                else:
                    price_unit = product.lst_price

                invoice_lines.append(Command.create({
                    'product_id': product.id,
                    'quantity': qty,
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

            invoice._onchange_partner_id()
            invoice._compute_amount()

            if len(invoice.line_ids) < 2:
                return self._response({'status': 'error', 'message': 'El cliente no tiene cuenta contable configurada'}, 400)

            return self._response({
                'status': 'success',
                'invoice': invoice.id,
                'message': 'factura creada'
            })

        except Exception as e:
            _logger.exception('Error en API HTTP')
            return self._response({'status': 'error', 'message': str(e)}, 500)

    @route('/api/payment', type='http', auth='public', methods=['POST'], csrf=False)
    def register_payment(self, **kw):
        """
        Estructura del JSON esperada:
        {
            "rif": "30292222",
            "amount": 150.00,
            "date": "2023-12-01",
            "payment_reference": "REF12345",
            "bank_reference": "0102030405",
            "journal_code": "BNK1",       <-- Código corto del diario en Odoo
            "payment_method_code": "manual" <-- Opcional (manual, inbound_credit_card, etc)
        }
        """
        data = {}
        try:
            raw_data = request.httprequest.data
            if not raw_data:
                return self._response({'status': 'error', 'message': 'Empty body'}, 400)

            try:
                data = json.loads(raw_data)
            except ValueError:
                return self._response({'status': 'error', 'message': 'JSON invalid'}, 400)

            # --- Extracción de datos ---
            vat = data.get('rif')
            amount = float(data.get('amount', 0.0))
            payment_date = data.get('date', fields.Date.today())
            reference = data.get('payment_reference')
            journal_code = data.get('journal_code')
            bank_reference = data.get('bank_reference')

            # --- Validaciones Básicas ---

            if not bank_reference:
                return self._response({'status': 'error','message': 'Falta la referencia bancaria o pago móvil'}, 400)
            if not vat:
                return self._response({'status': 'error', 'message': 'Falta el RIF'}, 400)
            if amount <= 0:
                return self._response({'status': 'error', 'message': 'El monto debe ser mayor a 0'}, 400)
            if not journal_code:
                return self._response({'status': 'error', 'message': 'Falta el código del diario (journal_code)'}, 400)

            # --- Buscar Cliente ---
            Contact = request.env['res.partner']
            clean_vat = str(vat).strip().upper().replace(' ', '')

            possible_vats = [clean_vat]

            if '-' in clean_vat:
                possible_vats.append(clean_vat.replace('-', ''))

            numeric_vat = ''.join(filter(str.isdigit, clean_vat))
            if numeric_vat and numeric_vat not in possible_vats:
                possible_vats.append(numeric_vat)

            if clean_vat.isdigit():
                possible_vats.extend([
                    f'V-{clean_vat}', f'V{clean_vat}',
                    f'J-{clean_vat}', f'J{clean_vat}',
                    f'E-{clean_vat}', f'G-{clean_vat}'
                ])

            contact = Contact.sudo().search([('vat', 'in', possible_vats)], limit=1)

            if not contact:
                return self._response({'status': 'error', 'message': f'Cliente con RIF {vat} no encontrado'}, 404)

            # --- Buscar Diario (Banco/Caja) ---
            Journal = request.env['account.journal']
            journal = Journal.sudo().search([
                ('code', '=', journal_code),
                ('type', 'in', ('bank', 'cash')),
                ('company_id', '=', request.env.company.id)
            ], limit=1)

            if not journal:
                return self._response({'status': 'error', 'message': f'Diario con código {journal_code} no encontrado'}, 404)

            # --- Buscar Método de Pago (Payment Method Line) ---
            payment_method_line = journal.inbound_payment_method_line_ids.filtered(
                lambda x: x.code == 'manual'  # Por defecto usamos 'manual'
            )

            # Si se envió un método específico en el JSON, intentamos buscarlo
            req_method_code = data.get('payment_method_code')
            if req_method_code:
                custom_method = journal.inbound_payment_method_line_ids.filtered(
                    lambda x: x.code == req_method_code
                )
                if custom_method:
                    payment_method_line = custom_method

            if not payment_method_line:
                payment_method_line = journal.inbound_payment_method_line_ids[:1]

            # --- Crear el Pago ---
            AccountPayment = request.env['account.payment']

            payment_vals = {
                'partner_id': contact.id,
                'amount': amount,
                'date': payment_date,
                'ref': reference,
                'journal_id': journal.id,
                'payment_type': 'inbound',       # 'inbound' = Cliente nos paga a nosotros
                'partner_type': 'customer',
                'payment_method_line_id': payment_method_line.id,
                'company_id': request.env.company.id,
                'concept': bank_reference,
            }

            payment = AccountPayment.sudo().create(payment_vals)

            # --- Confirmar el Pago (Postear) ---
            payment.action_post()

            return self._response({
                'status': 'success',
                'payment_id': payment.id,
                'payment_name': payment.name,
                'message': 'Pago registrado exitosamente'
            })

        except Exception as e:
            _logger.exception('Error registrando pago via API')
            return self._response({'status': 'error', 'message': str(e)}, 500)

    def _response(self, data, status=200):
        # * Helper para dar una respuesta JSON para el type='http'
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')],
            status=status
        )
