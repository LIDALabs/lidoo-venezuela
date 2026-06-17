# Cambios en retenciones - Junio 2026

Este documento resume los arreglos aplicados al módulo de retenciones (`l10n_ve_payment_extension`). Está escrito en lenguaje claro para que cualquier usuario del sistema entienda qué fallaba y qué se corrigió.

---

## 1. Error al aprobar una retención

### Qué pasaba
Al crear una retención (IVA, ISLR o Municipal) y apretar el botón **Aprobar**, el sistema mostraba un error de Odoo del tipo:

> `Expected singleton: account.move()`

Esto pasaba porque el pago que genera la retención quedaba "desconectado" de la línea de retención. Como resultado, cuando el sistema intentaba reconciliar el pago con la factura, no encontraba la factura asociada y explotaba.

### Cómo se reproducía
- Crear una retención de cliente o proveedor.
- Agregar la línea de retención con la factura correspondiente.
- Apretar **Aprobar**.
- El sistema fallaba con el error de `account.move()`.

### Qué se arregló
Se cambió la forma en que el sistema crea el pago de la retención. Ahora el pago se crea primero y **después** se le asigna la línea de retención, garantizando que la relación quede bien hecha.

**Archivo afectado:** `l10n_ve_payment_extension/models/account_retention.py`

### Resultado
Ahora se puede aprobar la retención sin errores. El pago se crea automáticamente, se vincula con la línea y se reconcilia con la factura.

---

## 2. Número de comprobante editable en retenciones de proveedor

### Qué pasaba
En las retenciones de **cliente**, el campo **Nro de Comprobante** se podía editar manualmente. En cambio, en las retenciones de **proveedor**, el campo aparecía bloqueado y el sistema generaba el número automáticamente.

En Venezuela, para ciertas operaciones de proveedor se necesita poder ingresar el número de comprobante a mano, igual que en las de cliente.

### Qué se arregló
Se desbloqueó el campo **Nro de Comprobante** en las tres vistas de retenciones (IVA, ISLR y Municipal), permitiendo editarlo también cuando la retención es de proveedor.

**Archivos afectados:**
- `l10n_ve_payment_extension/views/account_retention_iva.xml`
- `l10n_ve_payment_extension/views/account_retention_islr.xml`
- `l10n_ve_payment_extension/views/account_retention_municipal.xml`

### Comportamiento actual
- Si se deja el campo **Nro de Comprobante** vacío en una retención de proveedor, el sistema sigue generando uno automáticamente.
- Si se escribe un número manual, el sistema respeta ese número.
- Para retenciones de cliente, el campo sigue siendo obligatorio.

---

## Cómo usar el flujo correcto de retenciones

1. **Crear la factura** de cliente o proveedor y confirmarla.
2. Ir a **Contabilidad > Retenciones** y crear una nueva retención.
3. Seleccionar:
   - Tipo: `Factura de Cliente` o `Factura de Proveedor`.
   - Cliente / Proveedor.
   - Tipo de retención: IVA, ISLR o Municipal.
4. En la pestaña **Líneas de Retención**, agregar una línea y seleccionar la factura.
5. **No crear ningún pago manualmente** en la pestaña **Pagos**. Esa pestaña solo muestra el pago que el sistema generará automáticamente.
6. Apretar **Aprobar**.
7. El sistema:
   - Genera el pago de retención.
   - Lo vincula con la línea.
   - Reconcilia el pago con la factura.
   - Deja la factura como **Pagado parcialmente** (si la retención no cubre el total).

---

## Notas adicionales

- Una retención de IVA **no se calcula automáticamente** si la factura tiene impuestos en **0% EXEMPT** (exento de IVA). El cálculo requiere que la factura tenga un impuesto con tasa mayor a cero.
- Si se necesita retener sobre una factura exenta de IVA, revisar si corresponde crear una retención ISLR o Municipal en su lugar.

---

*Última actualización: junio 2026*
