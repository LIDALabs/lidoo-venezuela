# Localización Venezolana para Odoo

<!-- ## Propósito de las modificaciones -->

## Resumen de Módulos Modificaciones

- `l10n_ve_binaural`  
  Se portó el plan de cuentas de la versión 16.0. Se agrega una dependencia a `l10n_ve_binaural_pre`.

- `l10n_ve_invoice` y `l10n_ve_stock_account`  
  Se migra la funcionalidad del contador de impresiones de `l10n_ve_stock_account` a `l10n_ve_invoice` donde tiene mas sentido. Elimina la necesidad de `od_journal_sequence`.

## Resumen de Módulos Nuevos

- `l10n_ve_lida`  
  Un plan de cuenta de parte de LIDA.

- `l10n_ve_binaural_pre`  
  Este módulo crea una dependencia con `l10n_latam_invoice_document` y elimina la necesidad de `od_journal_sequence`.

- `l10n_ve_contact_extensions` 
  Implementa validación de forma de CI/RIF y agrega campos auxiliares para RIF completo y formateado.

- `l10n_ve_location_extensions`  
  Los campos de municipio y parroquia no son requeridos. Además coloca la validación de usuarios por RIF por defecto.
   
- `l10n_ve_igtf_extensions`  
  Permite asignar la base del I.G.T.F. previo al registro de los pagos. Este comportamiento es necesario cuando se hacen facturas digitales.

- `l10n_ve_invoice_extensions`  
  Hace que los documentos utilicen la funcionalidad nativa de notas de débito (`account_debit`) en lugar de la que `l10n_ve_invoice` implementa.

- `l10n_ve_withholding_extensions`  
  Oculta las pestañas de retenciones de views de `account.move` donde no deberían estar.
  

## Módulos de terceros requeridos/recomendados:

  - **Security Master (Recomendado)**  
    Función principal: Gestiona los reportes de auditoría exigidos por el SENIAT para cambios en modelos del sistema.  
    [Descargar en Odoo Store](https://apps.odoo.com/apps/modules/16.0/tk_security_master)

## Descargo de Responsabilidad

Esta localización se proporciona "tal cual", sin garantías de ningún tipo, expresas o implícitas. El uso de esta localización es bajo tu propia responsabilidad. CENPRO C.A. no se hace responsable por el uso indebido del software o por incumplimientos legales derivados de su implementación.

---

Queremos dar un especial agradecimiento al equipo de LIDA y de la Universidad José Antonio Páez.