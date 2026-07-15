# LIDA Integration API

Módulo de endpoints HTTP server-to-server para integraciones externas (IUTEPAL y otros sistemas).

## Autenticación

Todos los endpoints requieren:

- `auth='public'` + `csrf=False` (no usan sesión de usuario).
- Decorador `@require_api_key()` de `lida_api_auth`.
- Header: `X-Lidoo-Api-Key` (o query param `api_key`).
- La key se configura en **Ajustes → Integración API** (`api_auth.pull_api_key`).

No se usa JWT ni `auth='user'` para las integraciones server-to-server.

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
  "tasa": 725.75,
  "subtotal": 391.90,
  "taxes": 0.0,
  "total": 391.90,
  "desglose": {
    "base": 391.90,
    "iva": 0.0,
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
- Si `post: true`, postea (emite) la factura. Por defecto queda en borrador (`draft`).

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

**Response:**

```json
{
  "status": "success",
  "payment_id": 2626,
  "payment_name": "PBank/2026/00847",
  "partner_id": 15,
  "partner_created": false,
  "message": "Pago registrado exitosamente"
}
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

## Ejemplo de flujo completo IUTEPAL

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

