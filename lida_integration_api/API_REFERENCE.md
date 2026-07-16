# API Reference — LIDA Integration API

Referencia completa de los endpoints HTTP del módulo `lida_integration_api`
(Odoo 17, localización venezolana). Para la arquitectura interna ver
[DOCUMENTATION.md](DOCUMENTATION.md); para un resumen ver [README.md](README.md).

---

## Generalidades

### URL base

```
http(s)://<host>:<puerto>        # dev: http://localhost:10017
```

### Autenticación

Todos los endpoints requieren API key. Se configura en
**Ajustes → General Settings → Integration API** (módulo `lida_api_auth`),
con *Enable Pull Mode* activado.

| Header | Valor |
|---|---|
| `X-Lidoo-Api-Key` | la API key configurada (alternativa: query param `api_key`) |
| `Content-Type` | `application/json` |

Sin key o con key incorrecta → **401** `{"status": "error", "message": "No match Api Keys."}`.

### Habilitar/deshabilitar endpoints

En el mismo panel **Integration API**, bloque **API Endpoints**, cada endpoint
tiene su check (*Enable POST /api/quote*, */api/invoice*, */api/payment*).
Un endpoint deshabilitado responde **403**:

```json
{"status": "error", "message": "El endpoint /api/quote está deshabilitado"}
```

Por defecto los tres están habilitados.

### Formato de errores (todos los endpoints)

```json
{"status": "error", "message": "<descripción del problema>"}
```

| HTTP | Significado |
|---|---|
| `400` | Validación: falta un campo, formato incorrecto, o error de negocio de Odoo (`ValidationError`/`UserError`) |
| `401` | API key faltante o incorrecta |
| `403` | Endpoint deshabilitado en Ajustes |
| `404` | Recurso no encontrado (RIF, SKU, cotización, factura, diario) |
| `500` | Error inesperado del servidor (queda en el log de Odoo) |

### Convenciones

- Los montos en las respuestas van redondeados a **2 decimales**; `rate` a 4.
- `rif`: se acepta con o sin guión (`V12345678`, `V-12345678`, `12345678`).
- Moneda base: `VES`/`VEF`. Moneda alterna: `USD` (configurada en la compañía).

---

## 1. POST `/api/quote` — Crear cotización

Crea una `sale.order` **en borrador** y devuelve los totales que calcula Odoo
(precios de la lista de precios, IVA y tasa BCV de la localización — la API no
recalcula nada).

### Request

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `rif` | string | ✔ | RIF del cliente |
| `currency` | string | ✔ | `VES`/`VEF` (base) o `USD` (alterna) |
| `lines` | array | ✔ | Líneas de la cotización, mínimo 1 |
| `lines[].sku` | string | ✔ | `default_code` del producto |
| `lines[].quantity` | number | — | Cantidad, default `1` (debe ser > 0) |
| `create_partner_if_missing` | boolean | — | Crear el contacto si el RIF no existe (ver sección Contactos) |

```json
{
  "rif": "V12345678",
  "currency": "VES",
  "lines": [
    {"sku": "INSCRIPCION-01", "quantity": 1},
    {"sku": "MENSUALIDAD-01", "quantity": 2}
  ]
}
```

### Response `200`

| Campo | Tipo | Descripción |
|---|---|---|
| `status` | string | `"ok"` |
| `quote_id` | int | ID de la `sale.order` (usarlo luego en `/api/invoice`) |
| `partner_id` | int | ID del contacto |
| `partner_created` | boolean | `true` si el contacto se creó en esta llamada |
| `currency` | string | Moneda solicitada (los montos vienen en esta moneda) |
| `rate` | number | Tasa BCV del día usada (4 decimales) |
| `subtotal` | number | Base imponible |
| `taxes` | number | IVA |
| `total` | number | Total |
| `breakdown` | object | `{base, tax, total}` (mismos valores, agrupados) |
| `lines[]` | array | `{sku, quantity, price_unit, price_subtotal}` en la moneda solicitada |

```json
{
  "status": "ok",
  "quote_id": 42,
  "partner_id": 15,
  "partner_created": false,
  "currency": "VES",
  "rate": 725.75,
  "subtotal": 391.90,
  "taxes": 62.70,
  "total": 454.60,
  "breakdown": {"base": 391.90, "tax": 62.70, "total": 454.60},
  "lines": [
    {"sku": "INSCRIPCION-01", "quantity": 1.0, "price_unit": 391.90, "price_subtotal": 391.90}
  ]
}
```

### Errores propios

| HTTP | Cuándo |
|---|---|
| `400` | Falta `rif`, `currency` o `lines`; moneda no soportada; cantidad ≤ 0; sin moneda alterna configurada (para USD) |
| `404` | RIF no existe (sin `create_partner_if_missing`); SKU no existe |

---

## 2. POST `/api/invoice` — Crear factura de cliente

Crea una `account.move` tipo `out_invoice`. Dos modos **excluyentes**: desde
cotización (`quote_id`, recomendado) o directo con `lines` (legacy).

### Request — Modo cotización

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `rif` | string | ✔ | RIF del cliente (debe coincidir con el de la cotización) |
| `quote_id` | int | ✔ | ID devuelto por `/api/quote` |
| `payment_reference` | string | — | Referencia; se guarda en `payment_reference` y `ref` |
| `post` | boolean | — | `true` = emitir (postear) ya; default `false` (queda borrador) |
| `create_partner_if_missing` | boolean | — | Ver sección Contactos |

```json
{"rif": "V12345678", "quote_id": 42, "payment_reference": "REF123", "post": true}
```

Confirma la `sale.order` si está en borrador y genera la factura con
`_create_invoices()`, así **la factura conserva exactamente la matemática y la
tasa de la cotización**.

### Request — Modo legacy (`lines`)

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `rif` | string | ✔ | RIF del cliente |
| `lines` | array | ✔ | Igual que en quote; acepta además `price_unit` **o** `price_total` por línea (excluyentes; si no vienen, usa el precio del producto) |
| `payment_reference` | string | — | Referencia |
| `post` | boolean | — | `true` = emitir ya; default borrador |

### Response `200`

| Campo | Tipo | Descripción |
|---|---|---|
| `status` | string | `"success"` |
| `invoice_id` | int | ID de la factura (usarlo en `/api/payment`) |
| `invoice_number` | string | Número de factura (`"/"` si quedó en borrador) |
| `partner_id` | int | ID del contacto |
| `partner_created` | boolean | `true` si se creó |
| `state` | string | `"draft"` o `"posted"` |
| `quote_id` | int \| null | Cotización de origen (solo en modo cotización) |
| `sale_order` | string \| null | Nombre de la `sale.order` ligada (`invoice_origin`); evidencia del enlace nativo cotización↔factura |
| `control_number` | string | Número de control fiscal (`correlative`); vacío si aún en borrador |
| `amount` / `currency` | number / string | Total y moneda base |
| `foreign_amount` / `foreign_currency` | number / string | Total y moneda alterna (USD) |
| `payment_reference` | string | Referencia |
| `date` | string \| null | Fecha de la factura (`YYYY-MM-DD`) |
| `lines[]` | array | `{sku, name, quantity, price_unit, price_subtotal}` |
| `message` | string | Descripción |

> La respuesta **refleja exactamente el payload del webhook `invoice_posted`**
> (mismo constructor interno), más `status`, `partner_id`, `partner_created`,
> `state`, `quote_id`, `sale_order`. Así IUTEPAL recibe idénticos datos por la
> respuesta síncrona o por el webhook.

```json
{
  "status": "success",
  "partner_id": 15,
  "partner_created": false,
  "state": "posted",
  "quote_id": 42,
  "sale_order": "S00042",
  "invoice_id": 5358,
  "invoice_number": "F 00005996",
  "control_number": "00-00005996",
  "rif": "J316852075",
  "amount": 454.60,
  "currency": "VEF",
  "foreign_amount": 0.62,
  "foreign_currency": "USD",
  "payment_reference": "REF123",
  "date": "2026-07-16",
  "lines": [
    {"sku": "INSCRIPCION-01", "name": "Inscripción", "quantity": 1.0, "price_unit": 391.90, "price_subtotal": 391.90}
  ],
  "message": "factura creada"
}
```

> **Ligado cotización↔factura:** al usar `quote_id`, la factura se genera con
> `sale.order._create_invoices()`, que crea el enlace nativo de Odoo:
> `sale.order.invoice_ids` ↔ `account.move`, `account.move.invoice_origin` =
> nombre de la cotización, y `account.move.line.sale_line_ids` línea a línea.
> La cotización pasa a `invoice_status = 'invoiced'` y no puede volver a
> facturarse. El campo `sale_order` de la respuesta lo hace visible.

> Si `post: true`, además se dispara el webhook `invoice_posted` (ver README).

### Errores propios

| HTTP | Cuándo |
|---|---|
| `400` | Falta `rif`; faltan `quote_id` y `lines`; el RIF no coincide con la cotización; `price_unit` y `price_total` juntos; cliente sin cuenta contable |
| `404` | RIF no existe; `quote_id` no existe; producto no encontrado (en legacy responde 400) |

---

## 3. POST `/api/payment` — Registrar pago de cliente

Crea **y postea** un `account.payment` inbound. Si se indica una factura, el
pago se **concilia** contra ella; si no, queda como **anticipo**.

### Request

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `rif` | string | ✔ | RIF del cliente |
| `amount` | number | ✔ | Monto (> 0), en la moneda del diario (normalmente VES) |
| `bank_reference` | string | ✔ | Referencia bancaria / pago móvil (se guarda en `concept`) |
| `journal_code` | string | ✔ | Código corto del diario (`account.journal.code`, tipo bank/cash) |
| `payment_method_code` | string | — | `code` del método (`manual`) o `name` de la línea (`Transferencia`, `Pago móvil`; case-insensitive). Default: primera línea del diario |
| `date` | string | — | `YYYY-MM-DD`; default hoy |
| `payment_reference` | string | — | Referencia externa (se guarda en `ref`) |
| `invoice_id` | int | — | Factura a conciliar (excluyente con `invoice_number`) |
| `invoice_number` | string | — | Número de factura a conciliar (ej. `"F 00005996"`) |
| `create_partner_if_missing` | boolean | — | Ver sección Contactos |

```json
{
  "rif": "V12345678",
  "amount": 5000.00,
  "date": "2026-07-16",
  "payment_reference": "REF123",
  "bank_reference": "010203",
  "journal_code": "BNK1",
  "payment_method_code": "manual",
  "invoice_id": 5358
}
```

### Conciliación

- Con `invoice_id`/`invoice_number`: concilia con `js_assign_outstanding_line`
  (mecanismo nativo de Odoo). **Parciales permitidos** (la factura queda
  `partial`). Si `amount` supera el saldo, se aplica hasta el saldo y el resto
  queda como crédito a favor del cliente (`excess_amount`).
- Sin factura: el pago es un **anticipo** (`is_advance: true`), sin conciliar.

### Response `200`

| Campo | Tipo | Descripción |
|---|---|---|
| `status` | string | `"success"` |
| `payment_id` | int | ID del pago |
| `payment_name` | string | Número del pago (ej. `PBank/2026/00847`) |
| `partner_id` | int | ID del contacto |
| `partner_created` | boolean | `true` si se creó |
| `is_advance` | boolean | `true` = anticipo (sin factura) |
| `message` | string | Descripción |

Solo cuando se indicó factura, además:

| Campo | Tipo | Descripción |
|---|---|---|
| `invoice_id` | int | Factura conciliada |
| `invoice_number` | string | Número de la factura |
| `invoice_payment_state` | string | `partial`, `paid` o `in_payment` (según config del diario) |
| `amount_applied` | number | Cuánto del pago se aplicó a la factura |
| `invoice_amount_residual` | number | Saldo pendiente de la factura después del pago |
| `excess_amount` | number | Excedente que quedó como crédito a favor |

> Igual que en factura, la respuesta **refleja el payload del webhook
> `payment_posted`** (mismo constructor: `amount`, `currency`, `foreign_amount`,
> `bank_reference`, `journal_code`, `payment_method_code`, `is_advance`,
> `invoice_ids`/`invoice_numbers`), más el detalle de conciliación cuando se
> indicó factura (`amount_applied`, `invoice_amount_residual`, `excess_amount`).

```json
{
  "status": "success",
  "partner_id": 15,
  "partner_created": false,
  "is_advance": false,
  "invoice_ids": [5358],
  "invoice_numbers": ["F 00005996"],
  "payment_id": 2626,
  "payment_name": "PBank/2026/00847",
  "rif": "J316852075",
  "amount": 5000.0,
  "currency": "VEF",
  "foreign_amount": 6.87,
  "foreign_currency": "USD",
  "payment_reference": "REF123",
  "bank_reference": "010203",
  "date": "2026-07-16",
  "journal_code": "BNK1",
  "payment_method_code": "manual",
  "invoice_id": 5358,
  "invoice_number": "F 00005996",
  "invoice_payment_state": "paid",
  "amount_applied": 5000.0,
  "invoice_amount_residual": 0.0,
  "excess_amount": 0.0,
  "message": "Pago registrado exitosamente"
}
```

> Siempre se dispara el webhook `payment_posted` (con `is_advance` e
> `invoice_numbers` completados al momento del envío).

### Errores propios

| HTTP | Cuándo |
|---|---|
| `400` | Falta `rif`, `bank_reference` o `journal_code`; `amount` ≤ 0 o no numérico; `date` con formato inválido; factura no posteada / de otro cliente / ya pagada; diario sin métodos de pago |
| `404` | RIF no existe; diario no encontrado; factura (`invoice_id`/`invoice_number`) no encontrada |

---

## Contactos: `create_partner_if_missing`

Los tres endpoints aceptan `create_partner_if_missing: true`. Si el RIF no
existe, crea el contacto con estos campos (en el mismo body del request):

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `name` | string | ✔ | Nombre del contacto |
| `street` | string | ✔ | Dirección |
| `state_id` | string \| int | ✔ | Estado (nombre, código o ID) |
| `municipality` | string \| int | ✔ | Municipio (nombre o ID) |
| `zip_code_id` | string \| int | ✔ | Código postal (código o ID) |
| `street2` | string | — | Dirección línea 2 |
| `city_id` | string \| int | — | Ciudad (nombre o ID) |
| `phone` / `mobile` / `email` | string | — | Datos de contacto |

- Si el RIF ya existe, se usa el contacto existente y `partner_created: false`.
- Si falta un campo obligatorio → `400` con la lista de faltantes.
- Estado/municipio/código postal inexistentes → `404`.

---

## Flujo completo recomendado (IUTEPAL)

```bash
export ODOO_URL="http://localhost:10017"
export KEY="TU_API_KEY"

# 1. Cotizar (el alumno elige conceptos)
curl -sS -X POST "$ODOO_URL/api/quote" \
  -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"V12345678","currency":"VES","lines":[{"sku":"INSCRIPCION-01","quantity":1}]}'
# -> guardar quote_id y total

# 2. Facturar (el alumno pagó en la pasarela)
curl -sS -X POST "$ODOO_URL/api/invoice" \
  -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"V12345678","quote_id":42,"payment_reference":"REF123","post":true}'
# -> guardar invoice_id

# 3. Registrar el pago conciliado a la factura
curl -sS -X POST "$ODOO_URL/api/payment" \
  -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"V12345678","amount":454.60,"invoice_id":5358,"payment_reference":"REF123","bank_reference":"010203","journal_code":"BNK1","payment_method_code":"manual"}'
# -> invoice_payment_state: "paid"
```

Cada paso emite además su webhook (`invoice_posted`, `payment_posted`) con
`source: "api"` — ver el contrato de webhooks en [README.md](README.md#webhooks-outbound).

---

## Suite de pruebas

```bash
KEY=... RIF=... SKU=... JOURNAL=... ./tests_curl.sh
```

Cubre autenticación, los 3 endpoints, validaciones de error y deja eventos
de webhook disparados para verificar en el receptor (`webhook_receiver.py`).
