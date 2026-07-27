# Guía de pruebas — LIDA Integration API

Paso a paso para probar **todo** el módulo: los 3 endpoints, el ligado
cotización↔factura, la conciliación de pagos y los webhooks outbound.

> Referencia de campos: [API_REFERENCE.md](API_REFERENCE.md).

---

## 0. Preparación (una sola vez)

### Variables de entorno (para los `curl`)

```bash
export URL="http://localhost:10017"
export KEY="a46b736607db9ad31a0570ab86d29bbb1913f1b3d21fddf9c222f1f77a4e9a13"
export RIF="J316852075"      # cliente de prueba
export SKU="test1"           # producto con default_code
export JOURNAL="Bank"        # código de diario banco/caja
```

### Configuración en Odoo — **Ajustes → General Settings → Integration API**

- **API key**: la de `$KEY` (Enable Pull Mode activado).
- **API Endpoints**: los 3 checks encendidos.
- **Outbound Webhooks**:
  - *Enable Outbound Webhooks*: ✓
  - *Webhook URL*: `http://host.docker.internal:9999`
  - *Webhook Secret*: `test123`
  - *Send webhook on invoice posted*: ✓
  - *Send webhook on payment posted*: ✓

### Receptor de webhooks (terminal aparte)

```bash
cd ~/Documentos/odoo-docker-dev
python3 webhook_receiver.py 9999 test123
```

Verifica que el contenedor alcanza tu host:

```bash
sudo docker compose exec odoo17 python3 -c "import socket; print(socket.gethostbyname('host.docker.internal'))"
```

---

## 1. Endpoint `/api/quote` (cotización)

### 1.1 Caso feliz — VES

```bash
curl -sS -X POST "$URL/api/quote" \
  -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"'"$RIF"'","currency":"VES","lines":[{"sku":"'"$SKU"'","quantity":1}]}'
```

✅ Esperado: `status: "ok"`, un `quote_id`, `total`, `rate`, `breakdown`, `lines`.
**Anotá el `quote_id`** para el paso 2.

### 1.2 Caso feliz — USD (moneda alterna)

```bash
curl -sS -X POST "$URL/api/quote" \
  -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"'"$RIF"'","currency":"USD","lines":[{"sku":"'"$SKU"'","quantity":2}]}'
```

✅ Los montos vienen en USD (convertidos con `rate`).

### 1.3 Errores

| Enviar | Esperado |
|---|---|
| `"lines"` ausente | `400` "Faltan las líneas" |
| `"currency":"EUR"` | `400` "Moneda no soportada" |
| `"sku":"NO-EXISTE"` | `404` "Producto no encontrado" |
| `"rif":"V000111222"` (sin `create_partner_if_missing`) | `404` "Cliente no encontrado" |

---

## 2. Endpoint `/api/invoice` (factura)

### 2.1 Desde cotización + emitir (el flujo real de IUTEPAL)

Usá el `quote_id` del paso 1.1:

```bash
curl -sS -X POST "$URL/api/invoice" \
  -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"'"$RIF"'","quote_id":QUOTE_ID,"payment_reference":"REF-1","post":true}'
```

✅ Esperado: `state: "posted"`, `invoice_number` real (ej. `F 00006003`),
`control_number`, `amount`, `foreign_amount`, `lines`, y **`sale_order`** (el
enlace con la cotización). **Anotá el `invoice_id`** para el paso 3.

> La respuesta trae los mismos campos que el webhook `invoice_posted`.

### 2.2 Verificar el ligado cotización↔factura

Reintentá facturar la MISMA cotización ya facturada:

```bash
curl -sS -X POST "$URL/api/invoice" \
  -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"'"$RIF"'","quote_id":QUOTE_ID}'
```

✅ Esperado: error "No se pudo generar la factura desde la cotización" — porque
la `sale.order` ya está `invoiced`. Esto **prueba** que están ligadas.

### 2.3 Flujo legacy con `lines` (queda en borrador)

```bash
curl -sS -X POST "$URL/api/invoice" \
  -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"'"$RIF"'","payment_reference":"REF-2","lines":[{"sku":"'"$SKU"'","quantity":1}]}'
```

✅ `state: "draft"` (no mandé `post:true`). Agregá `"post":true` para emitir.

### 2.4 Errores

| Enviar | Esperado |
|---|---|
| `"quote_id":99999999` | `404` "Cotización no encontrada" |
| sin `quote_id` ni `lines` | `400` "Faltan quote_id o lines" |

---

## 3. Endpoint `/api/payment` (pago)

### 3.1 Anticipo (sin factura)

```bash
curl -sS -X POST "$URL/api/payment" \
  -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"'"$RIF"'","amount":50,"payment_reference":"REF-3","bank_reference":"111","journal_code":"'"$JOURNAL"'","payment_method_code":"manual"}'
```

✅ Esperado: `status: "success"`, `is_advance: true`, `payment_name`.

### 3.2 Conciliado a una factura (parcial)

Usá el `invoice_id` del paso 2.1:

```bash
curl -sS -X POST "$URL/api/payment" \
  -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"'"$RIF"'","amount":100,"invoice_id":INVOICE_ID,"payment_reference":"REF-4","bank_reference":"222","journal_code":"'"$JOURNAL"'","payment_method_code":"manual"}'
```

✅ Esperado: `is_advance: false`, `invoice_payment_state` (`partial` o `paid`),
`amount_applied`, `invoice_amount_residual`, `excess_amount`, y
`invoice_numbers`. Verificá en la UI que la factura muestra el pago aplicado.

### 3.3 Por número de factura (en vez de id)

```bash
curl -sS -X POST "$URL/api/payment" \
  -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"'"$RIF"'","amount":10,"invoice_number":"F 00006003","bank_reference":"333","journal_code":"'"$JOURNAL"'"}'
```

### 3.4 Errores

| Enviar | Esperado |
|---|---|
| sin `bank_reference` | `400` "Falta la referencia bancaria" |
| `"amount":0` | `400` "El monto debe ser mayor a 0" |
| `"journal_code":"ZZZZ"` | `404` "Diario no encontrado" |
| `"invoice_id":99999999` | `404` "Factura no encontrada" |
| `"date":"15-07-2026"` | `400` "use YYYY-MM-DD" |
| factura de otro RIF | `400` "no pertenece al cliente" |
| factura ya pagada | `400` "ya está pagada" |

---

## 4. Autenticación y toggles

### 4.1 Sin key / key incorrecta

```bash
curl -sS -o /dev/null -w "%{http_code}\n" -X POST "$URL/api/quote" \
  -H "Content-Type: application/json" -d '{}'                      # -> 401
```

### 4.2 Endpoint deshabilitado

En Ajustes desmarcá *Enable POST /api/quote*, guardá, y repetí 1.1:

✅ Esperado: `403` "El endpoint /api/quote está deshabilitado". Volvé a marcarlo.

---

## 5. Webhooks outbound

Con el receptor corriendo y los webhooks configurados (paso 0):

### 5.1 Envío automático al postear

Al ejecutar 2.1 (factura con `post:true`) y 3.1/3.2 (pagos), el webhook se
dispara **solo, en segundos** (vía `ir.cron._trigger()`).

En la terminal del receptor deberías ver:
- `invoice_posted` — `source: "api"`, con `control_number`, `foreign_amount`, `lines`.
- `payment_posted` — `source: "api"`, `is_advance` e `invoice_numbers`.
- Cada uno con `Firma HMAC: ✅ VÁLIDA`.

### 5.2 Desde la UI (flujo caja)

Postea una factura o un pago **desde la interfaz de Odoo**.

✅ Esperado: llega el webhook con `source: "odoo"`.

### 5.3 Toggle por tipo de evento

En Ajustes desmarcá *Send webhook on payment posted*, guardá, y postea un pago:

✅ Esperado: **no** llega webhook de pago (pero sí seguirían los de factura).
Volvé a marcarlo.

### 5.4 Anti-duplicado

Restablecé a borrador una factura ya posteada y postéala de nuevo (< 5 min):

✅ Esperado: **no** llega un segundo webhook. En el log de Odoo:
`Skipping duplicated invoice_posted webhook`.

### 5.5 Reintentos y backoff

Cortá el receptor y relanzalo en modo fallo:

```bash
python3 webhook_receiver.py 9999 test123 --fail
```

Postea algo. El receptor responde `500` → en **Ajustes → Técnico → LIDA Webhook
Events** el evento queda `pending`, `attempts` sube y `next_attempt_at` se va a
+2, +4, +8 min. Relanzá sin `--fail`, adelantá `next_attempt_at` y corré el cron
manual → pasa a `sent`.

✅ Clave: mientras el webhook fallaba, la factura/pago se posteó **igual** en
Odoo (el fallo del webhook nunca revierte la operación contable).

---

## 6. Flujo completo end-to-end (Apidog o curl)

```bash
# 1) Cotizar
Q=$(curl -sS -X POST "$URL/api/quote" -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"'"$RIF"'","currency":"VES","lines":[{"sku":"'"$SKU"'","quantity":1}]}')
QID=$(echo "$Q" | python3 -c "import sys,json;print(json.load(sys.stdin)['quote_id'])")

# 2) Facturar y emitir
I=$(curl -sS -X POST "$URL/api/invoice" -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"'"$RIF"'","quote_id":'"$QID"',"payment_reference":"E2E-1","post":true}')
IID=$(echo "$I" | python3 -c "import sys,json;print(json.load(sys.stdin)['invoice_id'])")

# 3) Pagar conciliando a la factura
curl -sS -X POST "$URL/api/payment" -H "X-Lidoo-Api-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"rif":"'"$RIF"'","amount":100,"invoice_id":'"$IID"',"payment_reference":"E2E-1","bank_reference":"010203","journal_code":"'"$JOURNAL"'"}'
```

Al terminar: 2 webhooks (`invoice_posted`, `payment_posted`) en el receptor, y
en Odoo la cotización `invoiced`, la factura con su pago aplicado.

---

## 7. Suite automática

Los casos 1–4 (sin webhooks) están en `tests_curl.sh`:

```bash
KEY=$KEY RIF=$RIF SKU=$SKU JOURNAL=$JOURNAL ./tests_curl.sh
```

Corre ~23 casos con ✔/✘ comparando el código HTTP esperado.
