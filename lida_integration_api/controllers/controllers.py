import logging
import json
import re

from odoo import http, fields
from odoo.exceptions import ValidationError, UserError
from odoo.http import request, route
from odoo.fields import Command
from odoo.addons.lida_api_auth.decorators import require_api_key

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

    # -------------------------------------------------------------------------
    # Helpers comunes
    # -------------------------------------------------------------------------
    def _json_response(self, data, status=200):
        """Devuelve una respuesta JSON uniforme para endpoints type='http'."""
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')],
            status=status
        )

    def _find_partner_by_rif(self, vat):
        """
        Busca un res.partner a partir de un RIF venezolano.

        Normaliza variantes como V12345678, V-12345678, 12345678 y busca
        primero usando los campos de l10n_ve_contact (prefix_vat + vat),
        con fallback a búsqueda directa en el campo vat para contactos legacy.

        :param vat: str con el RIF recibido (ej. 'V12345678')
        :return: res.partner | None
        """
        if not vat:
            return None

        clean = str(vat).strip().upper().replace(' ', '').replace('-', '')
        if not clean:
            return None

        partner = None

        # 1. Buscar por prefix_vat + vat usando la convención de l10n_ve_contact
        prefix_match = re.match(r'^([VJEGPC])(\d+)$', clean)
        if prefix_match:
            prefix = prefix_match.group(1)
            number = prefix_match.group(2)
            partner = request.env['res.partner'].sudo().search([
                ('prefix_vat', '=', prefix),
                ('vat', '=', number),
            ], limit=1)

        # 2. Fallback: buscar directamente en el campo vat (legacy / sin prefix)
        if not partner:
            possible_vats = [clean]

            # Sin guión, agregamos variantes con guión
            if len(clean) > 1 and clean[0] in 'VJEGPC' and clean[1:].isdigit():
                possible_vats.append(f"{clean[0]}-{clean[1:]}")
            elif clean.isdigit():
                for letter in 'VJEGP':
                    possible_vats.extend([
                        f'{letter}-{clean}', f'{letter}{clean}'
                    ])

            partner = request.env['res.partner'].sudo().search([
                ('vat', 'in', possible_vats)
            ], limit=1)

        return partner

    def _find_product_by_sku(self, sku):
        """
        Busca un product.product por su default_code (SKU).

        :param sku: str
        :return: product.product | None
        """
        if not sku:
            return None
        return request.env['product.product'].sudo().search([
            ('default_code', '=', str(sku).strip())
        ], limit=1)

    def _get_or_create_partner(self, vat, create_if_missing=False, partner_vals=None):
        """
        Busca un partner por RIF y opcionalmente lo crea si no existe.

        :param vat: RIF completo (ej. 'V12345678' o 'J-293710073').
        :param create_if_missing: si True, crea el partner si no se encuentra.
        :param partner_vals: dict con valores para crear el partner (name, street,
                             state_id, municipality, zip_code_id, city_id, phone, email, etc.).
        :return: tuple(partner, created, error_response | None)
                 created = True si el partner fue creado, False si ya existía.
        """
        partner = self._find_partner_by_rif(vat)
        if partner:
            return partner, False, None

        if not create_if_missing:
            return None, False, self._json_response(
                {'status': 'error', 'message': f'Cliente con RIF {vat} no encontrado'},
                404
            )

        partner_vals = partner_vals or {}
        clean = str(vat).strip().upper().replace(' ', '').replace('-', '')
        if not clean:
            return None, False, self._json_response(
                {'status': 'error', 'message': 'RIF inválido'},
                400
            )

        prefix_match = re.match(r'^([VJEGPC])(\d+)$', clean)
        if prefix_match:
            prefix = prefix_match.group(1)
            number = prefix_match.group(2)
        elif clean.isdigit():
            prefix = 'V'
            number = clean
        else:
            return None, False, self._json_response(
                {'status': 'error', 'message': f'Formato de RIF inválido: {vat}'},
                400
            )

        name = partner_vals.get('name')
        if not name:
            return None, False, self._json_response(
                {'status': 'error', 'message': 'Falta el nombre (name) para crear el contacto'},
                400
            )

        # Validación de campos obligatorios de dirección (l10n_ve_contact_extensions)
        required_address_fields = ['street', 'state_id', 'municipality', 'zip_code_id']
        missing = [f for f in required_address_fields if not partner_vals.get(f)]
        if missing:
            return None, False, self._json_response(
                {
                    'status': 'error',
                    'message': f'Faltan campos obligatorios de dirección: {", ".join(missing)}'
                },
                400
            )

        create_vals = {
            'name': name,
            'prefix_vat': prefix,
            'vat': number,
            'company_id': request.env.company.id,
            'country_id': request.env.ref('base.ve').id,
        }

        # Campos opcionales de dirección y contacto
        optional_fields = [
            'street', 'street2', 'phone', 'mobile', 'email'
        ]
        for field in optional_fields:
            if field in partner_vals:
                create_vals[field] = partner_vals[field]

        country_id = create_vals['country_id']

        # state_id: nombre o ID
        state_id = partner_vals.get('state_id')
        if isinstance(state_id, int):
            create_vals['state_id'] = state_id
        else:
            state = request.env['res.country.state'].sudo().search([
                ('country_id', '=', country_id),
                '|', ('name', 'ilike', state_id), ('code', 'ilike', state_id)
            ], limit=1)
            if not state:
                return None, False, self._json_response(
                    {'status': 'error', 'message': f'Estado no encontrado: {state_id}'},
                    404
                )
            create_vals['state_id'] = state.id

        # municipality: nombre o ID
        municipality = partner_vals.get('municipality')
        if isinstance(municipality, int):
            create_vals['municipality'] = municipality
        else:
            municipality_record = request.env['res.country.municipality'].sudo().search([
                ('country_id', '=', country_id),
                ('state_id', 'in', [create_vals['state_id']]),
                ('name', 'ilike', municipality)
            ], limit=1)
            if not municipality_record:
                return None, False, self._json_response(
                    {'status': 'error', 'message': f'Municipio no encontrado: {municipality}'},
                    404
                )
            create_vals['municipality'] = municipality_record.id

        # zip_code_id: código postal (name) o ID
        zip_code_id = partner_vals.get('zip_code_id')
        if isinstance(zip_code_id, int):
            create_vals['zip_code_id'] = zip_code_id
        else:
            zip_domain = [
                ('name', '=', str(zip_code_id).strip()),
            ]
            if 'municipality' in create_vals:
                zip_domain.append(('municipality_id', '=', create_vals['municipality']))
            zip_record = request.env['res.country.municipality.zip.code'].sudo().search(
                zip_domain, limit=1
            )
            if not zip_record:
                return None, False, self._json_response(
                    {'status': 'error', 'message': f'Código postal no encontrado: {zip_code_id}'},
                    404
                )
            create_vals['zip_code_id'] = zip_record.id

        # city_id: nombre o ID (opcional)
        city_id = partner_vals.get('city_id')
        if city_id:
            if isinstance(city_id, int):
                create_vals['city_id'] = city_id
            else:
                city = request.env['res.country.city'].sudo().search([
                    ('country_id', '=', country_id),
                    ('state_id', '=', create_vals['state_id']),
                    ('name', 'ilike', city_id)
                ], limit=1)
                if city:
                    create_vals['city_id'] = city.id

        _logger.info('Creando contacto desde API con vals: %s', create_vals)

        try:
            partner = request.env['res.partner'].sudo().create(create_vals)
        except Exception as exc:
            _logger.exception('Error creando contacto desde API')
            return None, False, self._handle_exception(exc, '_get_or_create_partner')

        return partner, True, None

    def _handle_exception(self, exc, endpoint_name):
        """
        Centraliza la respuesta de errores de Odoo.

        - ValidationError / UserError -> 400 con el mensaje de Odoo.
        - Cualquier otro error -> 500 + log completo.
        """
        if isinstance(exc, (ValidationError, UserError)):
            _logger.warning('Error de validación en %s: %s', endpoint_name, exc)
            return self._json_response({'status': 'error', 'message': str(exc)}, 400)

        _logger.exception('Error inesperado en %s', endpoint_name)
        return self._json_response({'status': 'error', 'message': str(exc)}, 500)

    @require_api_key()
    @route('/api/invoice', type='http', auth='public', methods=['POST'], csrf=False)
    def register_invoice(self, **kw):
        """
        Crea una factura de cliente (account.move out_invoice).

        Modos de uso:
        1. Desde cotización (quote_id):
           {
               "rif": "V12345678",
               "quote_id": 42,
               "payment_reference": "REF123",
               "post": false
           }
           Llama sale.order._create_invoices(). La factura queda en borrador
           a menos que se envíe "post": true.

        2. Flujo legacy con lines:
           {
               "rif": "V12345678",
               "payment_reference": "REF123",
               "lines": [
                   {"sku": "TRA", "quantity": 1}
               ]
           }
           Crea la factura directamente y siempre queda en borrador.
        """
        data = {}
        try:
            raw_data = request.httprequest.data
            if not raw_data:
                return self._json_response({'status': 'error', 'message': 'empty body'}, 400)
            try:
                data = json.loads(raw_data)
            except ValueError:
                return self._json_response({'status': 'error', 'message': 'JSON invalid'}, 400)

            vat = data.get('rif')
            payment_reference = data.get('payment_reference')
            quote_id = data.get('quote_id')
            post_invoice = bool(data.get('post', False))
            create_partner = bool(data.get('create_partner_if_missing', False))
            Company = request.env['res.company'].sudo().search([], limit=1, order='id')
            company_id = Company.id

            if not vat:
                return self._json_response({'status': 'error', 'message': 'Falta el RIF'}, 400)

            contact, partner_created, error = self._get_or_create_partner(vat, create_partner, data)
            if error:
                return error

            invoice = request.env['account.move']

            if quote_id:
                # ---- Modo cotización ----
                sale = request.env['sale.order'].sudo().browse(int(quote_id))
                if not sale.exists():
                    return self._json_response(
                        {'status': 'error', 'message': f'Cotización {quote_id} no encontrada'},
                        404
                    )
                if sale.partner_id.id != contact.id:
                    return self._json_response(
                        {'status': 'error', 'message': 'El RIF no coincide con el cliente de la cotización'},
                        400
                    )

                # _create_invoices requiere que la orden esté confirmada.
                if sale.state == 'draft':
                    sale.action_confirm()

                invoices = sale._create_invoices()
                if not invoices:
                    return self._json_response(
                        {'status': 'error', 'message': 'No se pudo generar la factura desde la cotización'},
                        400
                    )

                invoice = invoices[0]
                if payment_reference:
                    invoice.write({
                        'payment_reference': payment_reference,
                        'ref': payment_reference,
                    })

                if post_invoice:
                    invoice.action_post()

            else:
                # ---- Modo legacy con lines ----
                lines = data.get('lines')
                if not lines:
                    return self._json_response(
                        {'status': 'error', 'message': 'Faltan quote_id o lines'},
                        400
                    )

                invoice_lines = []
                Product = request.env['product.product']
                for line in lines:
                    sku = line.get('sku')
                    if not sku:
                        return self._json_response({'status': 'error', 'message': 'Falta SKU en una línea'}, 400)

                    product = Product.sudo().search([('default_code', '=', sku)], limit=1)
                    if not product:
                        return self._json_response({'status': 'error', 'message': f'Producto no encontrado: {sku}'}, 400)

                    if 'price_unit' in line and 'price_total' in line:
                        return self._json_response({
                            'status': 'error',
                            'message': f'Ambigüedad en producto {sku}: No puedes enviar "price_unit" y "price_total" al mismo tiempo.'
                        }, 400)

                    try:
                        qty = float(line.get('quantity', 1))
                    except (TypeError, ValueError):
                        return self._json_response(
                            {'status': 'error', 'message': f'Cantidad inválida para {sku}'},
                            400
                        )
                    price_unit = 0.0

                    if 'price_unit' in line:
                        try:
                            price_unit = float(line.get('price_unit'))
                        except (TypeError, ValueError):
                            return self._json_response(
                                {'status': 'error', 'message': f'price_unit inválido para {sku}'},
                                400
                            )
                    elif 'price_total' in line:
                        if qty == 0:
                            return self._json_response({'status': 'error', 'message': 'Cantidad no puede ser 0 si usas precio total'}, 400)
                        try:
                            price_total = float(line.get('price_total'))
                        except (TypeError, ValueError):
                            return self._json_response(
                                {'status': 'error', 'message': f'price_total inválido para {sku}'},
                                400
                            )
                        price_unit = price_total / qty
                    else:
                        price_unit = product.lst_price

                    invoice_lines.append(Command.create({
                        'product_id': product.id,
                        'quantity': qty,
                        'price_unit': price_unit
                    }))

                invoice = request.env['account.move'].sudo().create({
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
                return self._json_response({'status': 'error', 'message': 'El cliente no tiene cuenta contable configurada'}, 400)

            return self._json_response({
                'status': 'success',
                'invoice_id': invoice.id,
                'invoice_number': invoice.name,
                'partner_id': contact.id,
                'partner_created': partner_created,
                'state': invoice.state,
                'message': 'factura creada'
            })

        except Exception as e:
            return self._handle_exception(e, 'register_invoice')

    @require_api_key()
    @route('/api/quote', type='http', auth='public', methods=['POST'], csrf=False)
    def register_quote(self, **kw):
        """
        Crea una cotización (sale.order) en borrador y devuelve los totales
        calculados por Odoo usando la tasa BCV configurada.

        Estructura del JSON esperada:
        {
            "rif": "V12345678",
            "currency": "VES",
            "lines": [
                {"sku": "INSCRIPCION-01", "quantity": 1}
            ]
        }

        La moneda puede ser "VES"/"VEF" (moneda base de la compañía) o "USD"
        (moneda alterna configurada en la compañía).
        """
        try:
            raw_data = request.httprequest.data
            if not raw_data:
                return self._json_response({'status': 'error', 'message': 'empty body'}, 400)

            try:
                data = json.loads(raw_data)
            except ValueError:
                return self._json_response({'status': 'error', 'message': 'JSON invalid'}, 400)

            vat = data.get('rif')
            currency_code = data.get('currency')
            lines = data.get('lines')
            create_partner = bool(data.get('create_partner_if_missing', False))

            if not vat:
                return self._json_response({'status': 'error', 'message': 'Falta el RIF'}, 400)
            if not currency_code:
                return self._json_response({'status': 'error', 'message': 'Falta la moneda (currency)'}, 400)
            if not lines:
                return self._json_response({'status': 'error', 'message': 'Faltan las líneas (lines)'}, 400)

            currency_code = str(currency_code).strip().upper()
            base_currency = request.env.company.currency_id
            foreign_currency = request.env.company.currency_foreign_id

            # Normalizamos VES/VEF como moneda base
            is_base_currency = currency_code in ('VES', 'VEF')
            if not is_base_currency and currency_code != 'USD':
                return self._json_response(
                    {'status': 'error', 'message': f'Moneda no soportada: {currency_code}. Use VES o USD'},
                    400
                )

            if not is_base_currency and not foreign_currency:
                return self._json_response(
                    {'status': 'error', 'message': 'No hay moneda alterna configurada en la compañía'},
                    400
                )

            partner, partner_created, error = self._get_or_create_partner(vat, create_partner, data)
            if error:
                return error

            order_lines = []
            for line in lines:
                sku = line.get('sku')
                if not sku:
                    return self._json_response(
                        {'status': 'error', 'message': 'Falta SKU en una línea'},
                        400
                    )

                product = self._find_product_by_sku(sku)
                if not product:
                    return self._json_response(
                        {'status': 'error', 'message': f'Producto no encontrado: {sku}'},
                        404
                    )

                try:
                    qty = float(line.get('quantity', 1))
                except (TypeError, ValueError):
                    return self._json_response(
                        {'status': 'error', 'message': f'Cantidad inválida para {sku}'},
                        400
                    )
                if qty <= 0:
                    return self._json_response(
                        {'status': 'error', 'message': f'Cantidad inválida para {sku}'},
                        400
                    )

                order_lines.append(Command.create({
                    'product_id': product.id,
                    'product_uom_qty': qty,
                }))

            sale_vals = {
                'partner_id': partner.id,
                'currency_id': base_currency.id,
                'foreign_currency_id': foreign_currency.id if foreign_currency else False,
                'show_currency': not is_base_currency,
                'company_id': request.env.company.id,
                'order_line': order_lines,
            }

            sale = request.env['sale.order'].sudo().create(sale_vals)

            # Forzamos el cálculo de la tasa y los montos en moneda alterna
            sale._compute_rate()
            sale._compute_tax_totals()
            sale.order_line._compute_foreign_price()
            sale.order_line._compute_foreign_subtotal()

            # Determinamos los totales según la moneda solicitada
            if is_base_currency:
                subtotal = sale.amount_untaxed
                total = sale.amount_total
                taxes = total - subtotal
                rate = sale.foreign_rate or 0.0
            else:
                tax_totals = sale.tax_totals or {}
                subtotal = tax_totals.get('foreign_amount_untaxed', 0.0)
                total = tax_totals.get('foreign_amount_total', 0.0)
                taxes = total - subtotal
                rate = sale.foreign_rate or 0.0

            response_lines = []
            for line in sale.order_line:
                if is_base_currency:
                    line_price_unit = line.price_unit
                    line_subtotal = line.price_subtotal
                else:
                    line_price_unit = line.foreign_price
                    line_subtotal = line.foreign_subtotal

                response_lines.append({
                    'sku': line.product_id.default_code or '',
                    'quantity': line.product_uom_qty,
                    'price_unit': line_price_unit,
                    'price_subtotal': line_subtotal,
                })

            return self._json_response({
                'status': 'ok',
                'quote_id': sale.id,
                'partner_id': partner.id,
                'partner_created': partner_created,
                'currency': currency_code,
                'tasa': rate,
                'subtotal': subtotal,
                'taxes': taxes,
                'total': total,
                'desglose': {
                    'base': subtotal,
                    'iva': taxes,
                    'total': total,
                },
                'lines': response_lines,
            })

        except Exception as e:
            return self._handle_exception(e, 'register_quote')

    @require_api_key()
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
                return self._json_response({'status': 'error', 'message': 'Empty body'}, 400)

            try:
                data = json.loads(raw_data)
            except ValueError:
                return self._json_response({'status': 'error', 'message': 'JSON invalid'}, 400)

            # --- Extracción de datos ---
            vat = data.get('rif')
            create_partner = bool(data.get('create_partner_if_missing', False))
            try:
                amount = float(data.get('amount', 0.0))
            except (TypeError, ValueError):
                return self._json_response(
                    {'status': 'error', 'message': 'El monto (amount) debe ser numérico'},
                    400
                )
            payment_date = data.get('date', fields.Date.today())
            reference = data.get('payment_reference')
            journal_code = data.get('journal_code')
            bank_reference = data.get('bank_reference')

            # --- Validaciones Básicas ---

            if not bank_reference:
                return self._json_response({'status': 'error','message': 'Falta la referencia bancaria o pago móvil'}, 400)
            if not vat:
                return self._json_response({'status': 'error', 'message': 'Falta el RIF'}, 400)
            if amount <= 0:
                return self._json_response({'status': 'error', 'message': 'El monto debe ser mayor a 0'}, 400)
            if not journal_code:
                return self._json_response({'status': 'error', 'message': 'Falta el código del diario (journal_code)'}, 400)

            # --- Buscar/Crear Cliente ---
            contact, partner_created, error = self._get_or_create_partner(vat, create_partner, data)
            if error:
                return error

            # --- Buscar Diario (Banco/Caja) ---
            Journal = request.env['account.journal']
            journal = Journal.sudo().search([
                ('code', '=', journal_code),
                ('type', 'in', ('bank', 'cash')),
                ('company_id', '=', request.env.company.id)
            ], limit=1)

            if not journal:
                return self._json_response({'status': 'error', 'message': f'Diario con código {journal_code} no encontrado'}, 404)

            # --- Buscar Método de Pago (Payment Method Line) ---
            # Por defecto usamos la primera línea del diario.
            # Si el JSON trae payment_method_code, buscamos primero por 'code' y
            # luego por 'name' (case-insensitive), porque en la localización VE
            # varios métodos comparten el mismo code 'manual' (Transferencia,
            # Pago móvil, etc.).
            payment_method_line = journal.inbound_payment_method_line_ids[:1]

            req_method_code = data.get('payment_method_code')
            if req_method_code:
                req_method_str = str(req_method_code).strip()
                candidates = journal.inbound_payment_method_line_ids

                custom_method = candidates.filtered(lambda x: x.code == req_method_str)[:1]
                if not custom_method:
                    custom_method = candidates.filtered(
                        lambda x: x.name and x.name.strip().lower() == req_method_str.lower()
                    )[:1]

                if custom_method:
                    payment_method_line = custom_method

            if not payment_method_line:
                return self._json_response(
                    {'status': 'error', 'message': f'El diario {journal_code} no tiene métodos de pago entrante configurados'},
                    400
                )

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

            return self._json_response({
                'status': 'success',
                'payment_id': payment.id,
                'payment_name': payment.name,
                'partner_id': contact.id,
                'partner_created': partner_created,
                'message': 'Pago registrado exitosamente'
            })

        except Exception as e:
            return self._handle_exception(e, 'register_payment')
