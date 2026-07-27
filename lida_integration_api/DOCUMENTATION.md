# LIDA Integration API — Documentación técnica completa

Módulo de integración server-to-server para Odoo 17 con la localización
venezolana (`l10n_ve_*`). Tiene dos caras:

1. **API inbound (pull)**: endpoints HTTP para que sistemas externos creen
   cotizaciones, facturas y pagos en Odoo.
2. **Webhooks outbound (push)**: cuando se postea una factura o un pago de
   cliente, Odoo notifica a un sistema externo vía HTTP POST.

---

## Arquitectura general

```
Sistema externo ──POST /api/quote|invoice|payment──▶ Odoo (controllers.py)
                      X-Lidoo-Api-Key                      │
                                                            ▼
                                              Registros nativos de Odoo
                                        (sale.order / account.move / account.payment)
                                                            │
                                          action_post() ────┤ (facturas y pagos)
                                                            ▼
                                       lida_integration_api.webhook.event (cola)
                                                            │
                                              cron cada 5 minutos
                                                            ▼
Sistema externo ◀──POST Webhook URL (firmado HMAC-SHA256)──┘
```

Principio rector: **el módulo no recalcula nada fiscal** (IVA, tasa BCV,
retenciones, IGTF). Crea registros nativos de Odoo y deja que los módulos
`l10n_ve_*` apliquen su lógica; luego lee los totales resultantes.

### Estructura de archivos

| Archivo | Rol |
|---|---|
| `controllers/controllers.py` | Endpoints HTTP `/api/quote`, `/api/invoice`, `/api/payment` y helpers |
| `models/webhook_event.py` | Cola de eventos outbound, envío, reintentos y deduplicación |
| `models/account_move.py` | Hook en `action_post` de facturas → encola `invoice_posted` |
| `models/account_payment.py` | Hook en `action_post` de pagos → encola `payment_posted` |
| `models/res_config_settings.py` | Parámetros de configuración de webhooks |
| `data/ir_cron_data.xml` | Cron "LIDA: Process outbound webhook events" (cada 5 min) |
| `views/webhook_event_views.xml` | Vista de la cola de eventos |
| `views/res_config_settings_views.xml` | Panel de Ajustes → Integration API |
| `security/ir.model.access.csv` | Accesos del modelo de eventos |

---

## Fase 0 — Autenticación y helpers base

- Todos los endpoints usan `type='http'`, `auth='public'`, `csrf=False` y el
  decorador `@require_api_key()` del módulo `lida_api_auth`.
- Header obligatorio: **`X-Lidoo-Api-Key`** (alternativa: query param `api_key`).
- La key se configura en **Ajustes → General Settings → Integration API**
  (parámetro `api_auth.pull_api_key`). No se usa JWT ni sesión de usuario.
- **Toggles por endpoint**: en el mismo panel, bloque *API Endpoints*, cada
  endpoint se puede habilitar/deshabilitar individualmente. Se guardan como
  `"1"`/`"0"` en `lida_integration_api.endpoint_<nombre>_enable` (vía
  `get_values`/`set_values` explícitos, porque Odoo elimina los
  `ir.config_parameter` booleanos en `False` y con default `True` no se podría
  distinguir "nunca configurado" de "deshabilitado"). Un endpoint deshabilitado
  responde `403` (`_check_endpoint_enabled` en el controller).

Helpers comunes del controller:

- `_json_response(data, status)`: respuestas JSON uniformes con el status HTTP correcto.
- `_find_partner_by_rif(vat)`: busca al contacto por `prefix_vat` + `vat`
  (formato `l10n_ve_contact`) con fallback al formato legacy (todo el RIF en `vat`).
- `_find_product_by_sku(sku)`: busca el producto por `default_code`.
- `_get_or_create_partner(vat, create_if_missing, data)`: resuelve el contacto
  y, si `create_partner_if_missing: true`, lo crea con dirección completa.
- `_handle_exception(exc, endpoint)`: convierte `ValidationError`/`UserError`
  de Odoo en respuestas JSON 400 y errores inesperados en 500.

## Fase 1 — `POST /api/quote`

Crea una cotización (`sale.order`) **en borrador** y devuelve los totales que
calcula Odoo (subtotal, impuestos, total, tasa del día y desglose por línea).

- `currency`: `VES`/`VEF` (moneda base de la compañía) o `USD` (moneda alterna).
- `lines`: array `{sku, quantity}` — el precio sale de la lista de precios / producto.
- Acepta `create_partner_if_missing`.

## Fase 2 — `POST /api/invoice`

Crea una factura de cliente (`account.move` tipo `out_invoice`) de dos formas:

1. **Desde cotización** (`quote_id`): confirma la `sale.order` si está en
   borrador (`action_confirm`) y genera la factura con `_create_invoices()`.
   Valida que el `rif` coincida con el cliente de la cotización. Así la
   factura conserva exactamente la matemática de la cotización.
2. **Flujo legacy** (`lines`): crea la factura directamente con productos por SKU.

`post: true` emite (postea) la factura inmediatamente; por defecto queda en
borrador. Al postearse se dispara el webhook `invoice_posted` (Fase 5).

## Fase 3 — Creación de contactos

Todos los endpoints aceptan `create_partner_if_missing: true`.

- Obligatorios para crear: `name`, `street`, `state_id`, `municipality`, `zip_code_id`.
- Opcionales: `street2`, `city_id`, `phone`, `mobile`, `email`.
- Los campos de ubicación aceptan **nombre (string) o ID numérico**.
- Si el RIF ya existe se usa el contacto existente (`partner_created: false`).

## Fase 4 — `POST /api/payment`

Crea **y postea** un pago de cliente (`account.payment` inbound).

- `journal_code`: código corto del diario (`account.journal.code`, tipo bank/cash).
- `payment_method_code`: se busca primero por `code` de método de pago
  (`manual`, etc.) y luego por `name` de la línea (case-insensitive:
  `Transferencia`, `Pago móvil`…), porque en la localización VE varios métodos
  comparten el code `manual`. Si se omite, usa la primera línea del diario.
- `bank_reference` (obligatorio) se guarda en el campo `concept` del pago
  (campo de `l10n_ve_accountant`).
- Al postearse dispara el webhook `payment_posted` (Fase 5).

### Conciliación pago ↔ factura (`invoice_id` / `invoice_number`)

Si el request trae `invoice_id` o `invoice_number`, el pago se concilia contra
esa factura usando `js_assign_outstanding_line()` (mecanismo nativo de Odoo,
el mismo del widget "créditos pendientes"). Reglas:

- **Parciales permitidos**: la API no exige monto exacto; la factura queda en
  estado `partial` hasta completarse.
- **Sobrepago**: se aplica hasta el saldo pendiente; el excedente queda como
  crédito a favor del cliente (comportamiento nativo de Odoo). La respuesta
  informa `amount_applied` y `excess_amount`.
- **Sin factura** → el pago es un **anticipo** (`is_advance: true`), igual
  que el comportamiento histórico del endpoint.
- Validaciones: la factura debe existir, ser `out_invoice` posteada, del mismo
  partner que el RIF, y tener saldo pendiente.

## Fase 5 — Webhooks outbound

### Configuración

Todo en **Ajustes → General Settings → Integration API**:

| Campo | Parámetro (`ir.config_parameter`) | Descripción |
|---|---|---|
| Enable Outbound Webhooks | `lida_integration_api.webhook_enable` | Interruptor general |
| Webhook URL | `lida_integration_api.webhook_url` | URL destino del POST |
| Webhook Secret | `lida_integration_api.webhook_secret` | Secreto HMAC (opcional) |
| Max Attempts | `lida_integration_api.webhook_max_attempts` | Reintentos máximos (default 5) |

### Ciclo de vida de un evento

1. **Encolado** — El override de `action_post` en `account.move` /
   `account.payment` construye el payload y crea un registro
   `lida_integration_api.webhook.event` en estado `pending`.
   El encolado está envuelto en `try/except`: un fallo del webhook **nunca
   revierte el posteo** de la factura o el pago.
2. **Envío** — Al encolar, `enqueue()` dispara el cron inmediatamente con
   `ir.cron._trigger()` (se ejecuta tras el commit, típicamente en segundos).
   El cron *LIDA: Process outbound webhook events* además corre cada 5
   minutos como red de seguridad para reintentos. Toma hasta 100 eventos
   `pending`/`failed` con `attempts < max_attempts` y `next_attempt_at`
   vencido, y hace `POST` a la URL con `Content-Type: application/json`.
   El envío es **asíncrono**: nunca ocurre dentro del request/transacción
   del posteo, así un webhook lento o caído jamás afecta al cajero.
3. **Resultado** — HTTP 2xx → `sent`. Error → reintento con **backoff
   exponencial** (`2^intentos` minutos); al agotar `max_attempts` queda `failed`.

### Firma HMAC

Si hay secreto configurado, cada request lleva el header
**`X-Lidoo-Signature`** = `HMAC-SHA256(secret, body)` en hexadecimal.
El receptor debe recalcular la firma sobre el body **crudo** y comparar con
`hmac.compare_digest`.

### Anti-eco (`source`)

Todos los payloads incluyen el campo `source`:

- `"api"`: el posteo vino de `/api/invoice` (con `post: true`) o `/api/payment`.
  El sistema externo puede usarlo para ignorar el eco de operaciones que él
  mismo originó.
- `"odoo"`: el posteo vino de la UI de Odoo (flujo caja).

Se implementa pasando `lida_api_origin=True` en el contexto al llamar
`action_post()` desde los endpoints. Se optó por marcar el origen en vez de
suprimir el evento (`skip_webhook`) para no perder trazabilidad: el receptor
decide qué hacer con cada evento.

### Condiciones para encolar (anti-duplicados)

Solo se encola un evento cuando **todas** estas condiciones se cumplen:

- Webhooks habilitados en configuración.
- Factura: `move_type == 'out_invoice'`; pago: `payment_type == 'inbound'`.
- El registro quedó realmente en estado **`posted`** después de `action_post`.
- Tiene número asignado (`name` distinto de `/` y no vacío) — esto elimina el
  evento "fantasma" con datos de borrador (`invoice_number: "/"`, fecha `False`).
- No existe ya un evento `pending`/`sent` para el mismo registro (mismo
  `reference`, ej. `account.move,5358`) creado en los **últimos 5 minutos**
  (`_has_recent_event`) — protege contra doble click y flujos que llaman
  `action_post` más de una vez.

### Payload de factura (`invoice_posted`)

```json
{
  "event": "invoice_posted",
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
    {"sku": "INSCRIPCION-01", "name": "Inscripción", "quantity": 1.0,
     "price_unit": 7.26, "price_subtotal": 7.26}
  ]
}
```

| Campo | Origen |
|---|---|
| `invoice_number` | `move.name` (secuencia del diario) |
| `control_number` | `move.correlative` — número de control fiscal de `l10n_ve_invoice` |
| `rif` | `partner.prefix_vat + partner.vat` |
| `amount` | `move.amount_total`, redondeado a 2 decimales |
| `currency` | `move.currency_id.name` (VEF/VES) |
| `foreign_amount` | `move.tax_totals["foreign_amount_total"]` (calculado por `l10n_ve_tax` con la tasa de la factura), redondeado a 2 decimales; `null` si no hay moneda alterna |
| `foreign_currency` | `move.company_id.currency_foreign_id.name` (normalmente USD); `null` si no está configurada |
| `payment_reference` | `move.payment_reference` o `move.ref` |
| `date` | `move.invoice_date` en ISO (`YYYY-MM-DD`); `null` si no hay fecha |
| `lines[].price_unit` / `price_subtotal` | redondeados a 2 decimales |

### Payload de pago (`payment_posted`)

```json
{
  "event": "payment_posted",
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

| Campo | Origen |
|---|---|
| `payment_name` | `payment.name` (secuencia del diario) |
| `amount` | `payment.amount`, redondeado a 2 decimales |
| `foreign_amount` | Si `payment.currency_id` ya es la moneda alterna → `payment.amount` tal cual. Si no → `payment.amount * payment.foreign_inverse_rate` (factor de conversión con la tasa del día del pago, de `l10n_ve_accountant`). Fallback: `currency._convert()` estándar de Odoo. Siempre a 2 decimales; `null` sin moneda alterna |
| `foreign_currency` | `payment.company_id.currency_foreign_id.name`; `null` si no está configurada |
| `bank_reference` | `payment.concept` (donde `/api/payment` guarda la referencia bancaria) |
| `date` | `payment.date` en ISO; `null` si no hay fecha |
| `is_advance` | `true` si el pago no está conciliado con ninguna factura al momento del envío |
| `invoice_ids` / `invoice_numbers` | facturas conciliadas con el pago (arrays; un pago de caja puede cubrir varias). Se completan **al momento del envío** (`_refresh_payload`), porque la conciliación ocurre después de `action_post` tanto en la API como en el wizard de la UI |

### Monitoreo de la cola

Los eventos quedan en el modelo `lida_integration_api.webhook.event` con:
`event_type`, `payload` (JSON), `state` (`pending`/`sent`/`failed`),
`attempts`, `last_error`, `next_attempt_at` y `reference`
(`account.move,<id>` / `account.payment,<id>`). Un evento `failed` puede
reactivarse manualmente poniendo `attempts` en 0 y `state` en `pending`.

---

## Mejoras aplicadas a los endpoints (2026-07-16)

1. **Compañía consistente**: `/api/invoice` tomaba la primera compañía de la
   base de datos (`search([], limit=1)`); ahora usa `request.env.company`,
   igual que `/api/quote` y `/api/payment`.
2. **`post: true` en modo legacy**: el flag ahora también postea la factura
   en el flujo con `lines` (antes solo funcionaba con `quote_id`). Default
   sigue siendo borrador, sin cambio de comportamiento para clientes actuales.
3. **Redondeo en `/api/quote`**: `subtotal`, `taxes`, `total`, `breakdown` y
   líneas a 2 decimales; `rate` a 4 decimales (la tasa BCV necesita más
   precisión que los montos).
4. **Fecha del pago**: se valida el formato (`YYYY-MM-DD` → 400 claro en vez
   de 500) y `"date": null` cae al día de hoy.
5. **Reuso de helpers**: el modo legacy de `/api/invoice` usa
   `_find_product_by_sku` en vez de duplicar la búsqueda.
6. **Anti-eco**: campo `source` en los payloads de webhook (ver arriba).

## Fixes aplicados a webhooks (2026-07-16)

1. **Doble webhook por factura**: al confirmar una factura se generaban dos
   eventos, el primero con datos de borrador (`invoice_number: "/"`,
   `fecha: "False"`). Ahora se valida `state == 'posted'` + número asignado, y
   se deduplica por `reference` contra eventos `pending`/`sent` de los últimos
   5 minutos (`_has_recent_event` en `webhook_event.py`).
2. **Decimales sucios** (`7.2574700000000005`): todos los montos (`amount`,
   `foreign_amount`, `price_unit`, `price_subtotal`) se redondean a 2 decimales.
3. **Payload incompleto**: se agregaron `control_number`, `foreign_amount` y
   `foreign_currency` a factura, y `foreign_amount` / `foreign_currency` a pago.
4. **Fechas**: nunca se envía el string `"False"`; sin fecha se envía `null`.
5. **Robustez**: la construcción/encolado del payload va en `try/except` con
   log — un error del webhook no bloquea el posteo. La lectura de
   `tax_totals` también está protegida porque `l10n_ve_tax` lanza
   `ValidationError` si la compañía no tiene moneda alterna configurada.
6. **Manifest**: se declararon las dependencias reales `l10n_ve_tax` y
   `l10n_ve_accountant` (el código ya usaba `concept` y ahora usa
   `foreign_inverse_rate` y los totales foreign de `tax_totals`).

## Notas sobre monedas y tasas

- Moneda base de la compañía: **VEF/VES**. Moneda alterna
  (`company.currency_foreign_id`): normalmente **USD**.
- En facturas, los montos foreign los calcula `l10n_ve_tax` dentro de
  `tax_totals` usando la tasa registrada en la factura
  (`foreign_rate`/`foreign_inverse_rate` de `l10n_ve_accountant`/`l10n_ve_rate`).
- En pagos, `foreign_inverse_rate` es el **factor** que convierte el monto en
  moneda base a la moneda alterna, calculado con la tasa vigente a la fecha
  del pago (`res.currency.rate.compute_rate` de `l10n_ve_rate`).

## Dependencias del módulo

`base`, `lida_api_auth`, `sale_management`, `account`, `l10n_ve_contact`,
`l10n_ve_sale`, `l10n_ve_rate`, `l10n_ve_invoice`, `l10n_ve_tax`,
`l10n_ve_accountant`.

> Para request/response detallados de cada endpoint y ejemplos `curl` del
> flujo completo, ver [README.md](README.md).
