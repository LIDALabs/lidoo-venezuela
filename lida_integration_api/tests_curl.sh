#!/usr/bin/env bash
# Suite de pruebas curl — lida_integration_api (Fases 0 a 5 del plan IUTEPAL)
#
# Uso:
#   KEY=TU_API_KEY RIF=V12345678 SKU=INSCRIPCION-01 JOURNAL=BNK1 ./tests_curl.sh
#
# Variables opcionales:
#   ODOO_URL   default http://localhost:10017
#
# Para la Fase 5 (webhooks) dejá corriendo el receptor en otra terminal:
#   python3 webhook_receiver.py 9999 test123
set -u

ODOO_URL="${ODOO_URL:-http://localhost:10017}"
KEY="${KEY:?Falta KEY=<api key>}"
RIF="${RIF:?Falta RIF=<rif de prueba, ej V12345678>}"
SKU="${SKU:?Falta SKU=<default_code de un producto>}"
JOURNAL="${JOURNAL:?Falta JOURNAL=<codigo de diario bank/cash>}"

PASS=0; FAIL=0

title() { printf '\n\e[1;34m== %s ==\e[0m\n' "$1"; }

# call <esperado> <descripcion> <path> <json|SIN_KEY|KEY_MALA> [json cuando hay 3er modo]
call() {
    local expect="$1" desc="$2" path="$3" body="$4" auth="${5:-OK}"
    local hdr=(-H "Content-Type: application/json")
    case "$auth" in
        OK)       hdr+=(-H "X-Lidoo-Api-Key: $KEY");;
        SIN_KEY)  ;;
        KEY_MALA) hdr+=(-H "X-Lidoo-Api-Key: clave-incorrecta");;
    esac
    RESP=$(curl -sS -w '\n%{http_code}' -X POST "$ODOO_URL$path" "${hdr[@]}" -d "$body")
    CODE=$(echo "$RESP" | tail -1)
    BODY=$(echo "$RESP" | sed '$d')
    if [ "$CODE" = "$expect" ]; then
        printf '  \e[32m✔ %s (HTTP %s)\e[0m\n' "$desc" "$CODE"; PASS=$((PASS+1))
    else
        printf '  \e[31m✘ %s — esperaba %s, llegó %s\e[0m\n' "$desc" "$expect" "$CODE"; FAIL=$((FAIL+1))
        echo "$BODY" | python3 -m json.tool 2>/dev/null | head -5 | sed 's/^/    /'
    fi
}

json_get() { echo "$1" | python3 -c "import sys,json;print(json.load(sys.stdin).get('$2',''))" 2>/dev/null; }

# ---------------------------------------------------------------- FASE 0
title "FASE 0 — Autenticación"
call 401 "Sin API key -> rechazado"        /api/quote   '{"rif":"'"$RIF"'","currency":"VES","lines":[{"sku":"'"$SKU"'","quantity":1}]}' SIN_KEY
call 401 "API key incorrecta -> rechazado" /api/quote   '{"rif":"'"$RIF"'","currency":"VES","lines":[{"sku":"'"$SKU"'","quantity":1}]}' KEY_MALA
call 401 "Payment sin key -> rechazado"    /api/payment '{"rif":"'"$RIF"'","amount":1,"bank_reference":"x","journal_code":"'"$JOURNAL"'"}' SIN_KEY

# ---------------------------------------------------------------- FASE 1
title "FASE 1 — POST /api/quote"
call 200 "Cotización en VES" /api/quote '{"rif":"'"$RIF"'","currency":"VES","lines":[{"sku":"'"$SKU"'","quantity":1}]}'
QUOTE_VES="$BODY"
QUOTE_ID=$(json_get "$QUOTE_VES" quote_id)
echo "    quote_id=$QUOTE_ID  total=$(json_get "$QUOTE_VES" total) VES  rate=$(json_get "$QUOTE_VES" rate)"
call 200 "Cotización en USD (moneda alterna)" /api/quote '{"rif":"'"$RIF"'","currency":"USD","lines":[{"sku":"'"$SKU"'","quantity":1}]}'
echo "    total=$(json_get "$BODY" total) USD"
call 404 "SKU inexistente -> 404"      /api/quote '{"rif":"'"$RIF"'","currency":"VES","lines":[{"sku":"NO-EXISTE-999","quantity":1}]}'
call 400 "Sin lines -> 400"            /api/quote '{"rif":"'"$RIF"'","currency":"VES"}'
call 400 "Moneda inválida -> 400"      /api/quote '{"rif":"'"$RIF"'","currency":"EUR","lines":[{"sku":"'"$SKU"'","quantity":1}]}'
call 404 "RIF inexistente sin create -> 404" /api/quote '{"rif":"V99999999","currency":"VES","lines":[{"sku":"'"$SKU"'","quantity":1}]}'

# ---------------------------------------------------------------- FASE 2
title "FASE 2 — POST /api/invoice"
call 200 "Factura desde quote_id ($QUOTE_ID) con post:true" /api/invoice \
     '{"rif":"'"$RIF"'","quote_id":'"$QUOTE_ID"',"payment_reference":"REF-SUITE-1","post":true}'
INVOICE="$BODY"
INVOICE_ID=$(json_get "$INVOICE" invoice_id)
echo "    invoice_id=$INVOICE_ID  numero=$(json_get "$INVOICE" invoice_number)  estado=$(json_get "$INVOICE" state)"
call 200 "Factura legacy con lines (regresión, queda draft)" /api/invoice \
     '{"rif":"'"$RIF"'","payment_reference":"REF-SUITE-2","lines":[{"sku":"'"$SKU"'","quantity":1}]}'
call 404 "quote_id inexistente -> 404" /api/invoice '{"rif":"'"$RIF"'","quote_id":99999999}'
call 400 "Sin quote_id ni lines -> 400" /api/invoice '{"rif":"'"$RIF"'"}'

# ---------------------------------------------------------------- FASE 3
title "FASE 3 — Creación de contactos"
call 400 "create_partner sin campos de dirección -> 400" /api/quote \
     '{"rif":"V88888888","name":"Prueba Suite","create_partner_if_missing":true,"currency":"VES","lines":[{"sku":"'"$SKU"'","quantity":1}]}'
echo "    (la creación real de un contacto genera datos: probala a mano con street/state_id/municipality/zip_code_id)"

# ---------------------------------------------------------------- FASE 4
title "FASE 4 — POST /api/payment"
call 200 "Pago anticipo (sin factura)" /api/payment \
     '{"rif":"'"$RIF"'","amount":10,"payment_reference":"REF-SUITE-3","bank_reference":"111111","journal_code":"'"$JOURNAL"'","payment_method_code":"manual"}'
echo "    is_advance=$(json_get "$BODY" is_advance)  payment=$(json_get "$BODY" payment_name)"
if [ -n "$INVOICE_ID" ]; then
    call 200 "Pago parcial conciliado a factura $INVOICE_ID" /api/payment \
         '{"rif":"'"$RIF"'","amount":1,"invoice_id":'"$INVOICE_ID"',"payment_reference":"REF-SUITE-4","bank_reference":"222222","journal_code":"'"$JOURNAL"'","payment_method_code":"manual"}'
    echo "    is_advance=$(json_get "$BODY" is_advance)  estado_factura=$(json_get "$BODY" invoice_payment_state)  aplicado=$(json_get "$BODY" amount_applied)  saldo=$(json_get "$BODY" invoice_amount_residual)"
fi
call 400 "Sin bank_reference -> 400"  /api/payment '{"rif":"'"$RIF"'","amount":10,"journal_code":"'"$JOURNAL"'"}'
call 400 "Monto 0 -> 400"             /api/payment '{"rif":"'"$RIF"'","amount":0,"bank_reference":"x","journal_code":"'"$JOURNAL"'"}'
call 404 "Diario inexistente -> 404"  /api/payment '{"rif":"'"$RIF"'","amount":10,"bank_reference":"x","journal_code":"ZZZZ"}'
call 404 "invoice_id inexistente -> 404" /api/payment '{"rif":"'"$RIF"'","amount":10,"invoice_id":99999999,"bank_reference":"x","journal_code":"'"$JOURNAL"'"}'
call 400 "Fecha inválida -> 400"      /api/payment '{"rif":"'"$RIF"'","amount":10,"date":"15-07-2026","bank_reference":"x","journal_code":"'"$JOURNAL"'"}'

# ---------------------------------------------------------------- FASE 5
title "FASE 5 — Webhooks (verificación manual)"
cat <<'EOF'
  La suite ya generó eventos: 1 factura posteada + 2 pagos.
  En la terminal del receptor (webhook_receiver.py) deberían haber llegado
  en segundos:
    - invoice_posted (event)  source=api, con control_number y foreign_amount
    - payment_posted (event)  is_advance=true  (el anticipo)
    - payment_posted (event)  is_advance=false, invoice_numbers=[...] (el conciliado)
  Y en Odoo: Ajustes -> Técnico -> LIDA Webhook Events, todos en estado "sent".
  Falta probar a mano: factura/pago desde la UI (source=odoo), anti-duplicado
  (draft -> re-postear), y reintentos (receptor con --fail).
EOF

printf '\n\e[1mResultado: %d OK, %d fallidas\e[0m\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
