# LIDA Integration API

Módulo de endpoints HTTP server-to-server para integraciones externas.

> 📘 **Referencia completa de la API** (campos, tipos, respuestas y errores de
> cada endpoint): [API_REFERENCE.md](API_REFERENCE.md).
> 🧪 **Guía de pruebas paso a paso** (payloads de cada endpoint + webhooks):
> [TESTING.md](TESTING.md).
> Arquitectura interna y detalle de webhooks: [DOCUMENTATION.md](DOCUMENTATION.md).

## Autenticación

Todos los endpoints requieren:

- `auth='public'` + `csrf=False` (no usan sesión de usuario).
- Decorador `@require_api_key()` de `lida_api_auth`.
- Header: `X-Lidoo-Api-Key` (o query param `api_key`).
- La key se configura en **Ajustes → Integración API** (`api_auth.pull_api_key`).

No se usa JWT ni `auth='user'` para las integraciones server-to-server.

## Configuración

- API key: **Ajustes → General Settings → Integration API** (del módulo `lida_api_auth`).
- **API Endpoints**: en el mismo panel, cada endpoint (`/api/quote`, `/api/invoice`, `/api/payment`) tiene su check para habilitarlo/deshabilitarlo. Deshabilitado responde `403`. Por defecto los tres están habilitados.
- Webhooks outbound: activar *Enable Outbound Webhooks*, indicar *Webhook URL*, *Webhook Secret* y *Max Attempts*.
- **Webhooks por tipo de evento**: *Send webhook on invoice posted* y *Send webhook on payment posted* controlan por separado si se encola el evento al postear facturas y pagos. Ambos gobernados por el master *Enable Outbound Webhooks* (si el master está off, no se envía nada). Por defecto los dos están habilitados.

## Principios

- No se recalcula IVA, BCV, retenciones ni IGTF en el controller.
- Se crean registros nativos de Odoo (`sale.order`, `account.move`, `account.payment`) y se leen sus totales.
- La lógica fiscal la mantienen los módulos `l10n_ve_*`.

## Endpoints

### `POST /api/quote`

Crea una cotización (`sale.order`) en borrador y devuelve los totales calculados por Odoo.

**Request:**

```json
{
  "rif": "V12345678",
  "currency": "VES",
  "lines": [
    {"sku": "INSCRIPCION-01", "quantity": 1}
  ]
}
```

- `currency`: `VES`/`VEF` (moneda base de la compañía) o `USD` (moneda alterna).
- `lines`: array de objetos `{sku, quantity}`.
- `create_partner_if_missing`: boolean (opcional). Si es `true` y el RIF no existe, crea el contacto.
- `name`: string (requerido solo si se crea el contacto).

**Response:**

```json
{
  "status": "ok",
  "quote_id": 42,
  "partner_id": 15,
  "partner_created": false,
  "currency": "VES",
  "rate": 725.75,
  "subtotal": 391.90,
  "taxes": 0.0,
  "total": 391.90,
  "breakdown": {
    "base": 391.90,
    "tax": 0.0,
    "total": 391.90
  },
  "lines": [
    {"sku": "INSCRIPCION-01", "quantity": 1.0, "price_unit": 391.90, "price_subtotal": 391.90}
  ]
}
```

### `POST /api/invoice`

Crea una factura de cliente (`account.move` de tipo `out_invoice`).

**Modo 1 — desde cotización (`quote_id`):**

```json
{
  "rif": "V12345678",
  "quote_id": 42,
  "payment_reference": "REF123",
  "post": false
}
```

- Llama `sale.order._create_invoices()`.
- Valida que el `rif` coincida con el cliente de la cotización.
- Si `post: true`, postea (emite) la factura. Por defecto queda en borrador (`draft`). Aplica en ambos modos (`quote_id` y `lines`).

**Modo 2 — flujo legacy con `lines`:**

```json
{
  "rif": "V12345678",
  "payment_reference": "REF123",
  "lines": [
    {"sku": "INSCRIPCION-01", "quantity": 1}
  ]
}
```

**Response:**

```json
{
  "status": "success",
  "invoice_id": 5354,
  "invoice_number": "INV/2026/00001",
  "partner_id": 15,
  "partner_created": false,
  "state": "draft",
  "message": "factura creada"
}
```

### `POST /api/payment`

Crea y postea un pago de cliente (`account.payment`).

**Request:**

```json
{
  "rif": "V12345678",
  "amount": 5000.00,
  "date": "2026-07-15",
  "payment_reference": "REF123",
  "bank_reference": "010203",
  "journal_code": "BNK1",
  "payment_method_code": "manual"
}
```

- `journal_code`: código corto del diario (`account.journal.code`).
- `payment_method_code`: puede ser el `code` (`manual`) o el `name` de la línea de método de pago (`Transferencia`, `Pago móvil`, etc.). Si se omite, usa la primera línea del diario.
- `bank_reference` se guarda en el campo `concept` del pago.
- `invoice_id` **o** `invoice_number` (opcional): factura de cliente contra la que
  conciliar el pago. Si no se envía, el pago queda como **anticipo**
  (`is_advance: true`), sin conciliar.

**Conciliación:** usa el mecanismo nativo de Odoo (`js_assign_outstanding_line`).
Se admiten pagos **parciales** (la factura queda `partial`). Si el monto supera
el saldo pendiente, se aplica hasta el saldo y el excedente queda como crédito
a favor del cliente (`excess_amount`).

Validaciones (400/404): factura inexistente, no es factura de cliente, no está
emitida, no pertenece al RIF indicado, o ya está pagada.

**Response:**

```json
{
  "status": "success",
  "payment_id": 2626,
  "payment_name": "PBank/2026/00847",
  "partner_id": 15,
  "partner_created": false,
  "is_advance": false,
  "invoice_id": 5358,
  "invoice_number": "F 00005996",
  "invoice_payment_state": "partial",
  "amount_applied": 5000.0,
  "invoice_amount_residual": 2260.0,
  "excess_amount": 0.0,
  "message": "Pago registrado exitosamente"
}
```

Sin factura, la respuesta solo trae `is_advance: true` (sin los campos `invoice_*`).

## Webhooks outbound

Cuando se postea una **factura de cliente** (`out_invoice`) o un **pago de cliente**
(inbound), Odoo encola un evento y lo envía vía HTTP POST a la *Webhook URL*
configurada. El envío ocurre **segundos después del posteo**: al encolar se
dispara el cron con `ir.cron._trigger()` (post-commit); el intervalo de 5
minutos del cron queda como red de seguridad para reintentos. El POST nunca
ocurre dentro de la transacción del posteo.

- Firma: header `X-Lidoo-Signature` = HMAC-SHA256 del body con el *Webhook Secret* (solo si hay secreto configurado).
- Reintentos con backoff exponencial (`2^intentos` minutos) hasta *Max Attempts*; estados del evento: `pending` → `sent` / `failed`.
- **Anti-duplicados**: solo se encola si el registro está en estado `posted` y tiene número asignado (`name != "/"`), y no existe ya un evento `pending`/`sent` para el mismo registro en los últimos 5 minutos.
- **Anti-eco**: todos los payloads incluyen `source`: `"api"` si el posteo vino de `/api/invoice` o `/api/payment` (el receptor puede ignorar el eco de sus propias operaciones), `"odoo"` si vino de la UI (caja).
- Todos los montos van redondeados a 2 decimales. Si un dato no existe (p. ej. sin fecha o sin moneda alterna configurada), se envía `null`.

### Payload de factura (`invoice_posted`)

```json
{
  "event": "invoice_posted",
  "source": "odoo",
  "invoice_id": 5358,
  "invoice_number": "F 00005996",
  "control_number": "00-00005996",
  "rif": "J300016889",
  "amount": 7.26,
  "currency": "VEF",
  "foreign_amount": 0.01,
  "foreign_currency": "USD",
  "payment_reference": "F 00005996",
  "date": "2026-07-16",
  "lines": [
    {"sku": "INSCRIPCION-01", "name": "Inscripción", "quantity": 1.0, "price_unit": 7.26, "price_subtotal": 7.26}
  ]
}
```

- `control_number`: número de control fiscal (`account.move.correlative`, de `l10n_ve_invoice`).
- `foreign_amount`: total en moneda alterna (`tax_totals.foreign_amount_total`, de `l10n_ve_tax`).
- `foreign_currency`: nombre de la moneda alterna de la compañía (`company.currency_foreign_id`).

### Payload de pago (`payment_posted`)

```json
{
  "event": "payment_posted",
  "source": "api",
  "is_advance": false,
  "invoice_ids": [5358],
  "invoice_numbers": ["F 00005996"],
  "payment_id": 99,
  "payment_name": "PBank/2026/00010",
  "rif": "J300016889",
  "amount": 7.26,
  "currency": "VEF",
  "foreign_amount": 0.01,
  "foreign_currency": "USD",
  "payment_reference": "REF123",
  "bank_reference": "010203",
  "date": "2026-07-16",
  "journal_code": "BNK1",
  "payment_method_code": "manual"
}
```

- `foreign_amount`: monto convertido a la moneda alterna. Si el pago ya está en la moneda alterna se envía tal cual; si no, se usa `foreign_inverse_rate` (tasa del día del pago, de `l10n_ve_accountant`) y como último recurso la conversión estándar de Odoo.
- `bank_reference`: campo `concept` del pago.
- `is_advance`: `true` si al momento del envío el pago no está conciliado con ninguna factura; `false` si sí, con las facturas en `invoice_ids`/`invoice_numbers` (arrays: un pago de caja puede cubrir varias facturas). Estos campos se completan **al momento del envío** porque la conciliación ocurre después del posteo.

### Verificación de la firma (ejemplo del receptor)

```python
import hashlib, hmac

def is_valid(body_bytes, header_signature, secret):
    expected = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_signature)
```

## Códigos de error

- `400`: error de validación (datos faltantes, formato incorrecto, error de Odoo).
- `401`/`403`: API key inválida o faltante (lo devuelve `lida_api_auth`).
- `404`: recurso no encontrado (RIF, SKU, cotización, diario).
- `500`: error inesperado del servidor.

## Dependencias

- `lida_api_auth`
- `sale_management`
- `account`
- `l10n_ve_contact`
- `l10n_ve_sale`
- `l10n_ve_rate`
- `l10n_ve_invoice`
- `l10n_ve_tax` (totales en moneda alterna en `tax_totals`)
- `l10n_ve_accountant` (`concept` y `foreign_inverse_rate` en pagos)

## Crear contacto en cualquier endpoint

Todos los endpoints aceptan `create_partner_if_missing: true` y `name`:

```json
{
  "rif": "J12345678",
  "name": "Nombre del contacto",
  "create_partner_if_missing": true,
  "currency": "VES",
  "lines": [{"sku": "test1", "quantity": 1}],
  "street": "Av. Principal",
  "state_id": "Distrito Capital",
  "municipality": "Libertador",
  "zip_code_id": "1010",
  "city_id": "Caracas",
  "phone": "02121234567",
  "email": "test@example.com"
}
```

Si el RIF ya existe, se usa el contacto existente y `partner_created` será `false`.
Si no existe, se crea con `prefix_vat` + `vat` según `l10n_ve_contact` y `partner_created` será `true`.

Campos obligatorios para crear contacto: `name`, `street`, `state_id`, `municipality`, `zip_code_id`.
Campos opcionales: `street2`, `city_id`, `phone`, `mobile`, `email`.

`state_id`, `municipality`, `zip_code_id` y `city_id` pueden enviarse como nombre (string) o como ID numérico.

## Ejemplo de flujo completo

```bash
export ODOO_URL="http://localhost:10017"
export KEY="TU_API_KEY"

# 1. Cotización
curl -sS -X POST "$ODOO_URL/api/quote" \
  -H "X-Lidoo-Api-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"rif":"V12345678","currency":"VES","lines":[{"sku":"INSCRIPCION-01","quantity":1}]}'

# 2. Factura desde quote_id
curl -sS -X POST "$ODOO_URL/api/invoice" \
  -H "X-Lidoo-Api-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"rif":"V12345678","quote_id":42,"payment_reference":"REF123","post":true}'

# 3. Registrar pago
curl -sS -X POST "$ODOO_URL/api/payment" \
  -H "X-Lidoo-Api-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"rif":"V12345678","amount":5000,"payment_reference":"REF123","bank_reference":"010203","journal_code":"BNK1","payment_method_code":"manual"}'
```

## Notas

- El flujo `quote_id` mantiene la misma matemática de la cotización porque la factura se genera desde la `sale.order`.
- El flujo legacy con `lines` sigue funcionando exactamente igual que antes.
- Los errores de validación de Odoo (`ValidationError`, `UserError`) se devuelven como JSON con status 400.

