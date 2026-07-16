# -*- coding: utf-8 -*-
from odoo import fields, models

# Se guardan como "1"/"0" vía get_values/set_values (y no con config_parameter)
# porque Odoo elimina el ir.config_parameter cuando un Boolean queda en False,
# lo que haría imposible distinguir "nunca configurado" de "deshabilitado"
# con un default True.
TRUE_DEFAULT_PARAMS = {
    # Toggles por endpoint (403 si están off)
    "lida_endpoint_quote_enable": "lida_integration_api.endpoint_quote_enable",
    "lida_endpoint_invoice_enable": "lida_integration_api.endpoint_invoice_enable",
    "lida_endpoint_payment_enable": "lida_integration_api.endpoint_payment_enable",
    # Toggles por tipo de evento de webhook (no se encola si está off)
    "lida_webhook_invoice_enable": "lida_integration_api.webhook_invoice_enable",
    "lida_webhook_payment_enable": "lida_integration_api.webhook_payment_enable",
}


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    lida_webhook_enable = fields.Boolean(
        string="Habilitar Webhooks Salientes",
        config_parameter="lida_integration_api.webhook_enable",
        help="Notifica a sistemas externos cuando se emiten facturas y pagos.",
        default=False,
    )
    lida_webhook_url = fields.Char(
        string="URL del Webhook",
        config_parameter="lida_integration_api.webhook_url",
        help="URL a la que Odoo enviará los eventos vía HTTP POST.",
    )
    lida_webhook_secret = fields.Char(
        string="Secreto del Webhook",
        config_parameter="lida_integration_api.webhook_secret",
        help="Secreto compartido para firmar los payloads salientes (HMAC-SHA256, header X-Lidoo-Signature).",
    )
    lida_webhook_max_attempts = fields.Integer(
        string="Intentos Máximos",
        config_parameter="lida_integration_api.webhook_max_attempts",
        help="Cantidad máxima de intentos de entrega antes de marcar el evento como fallido.",
        default=5,
    )
    lida_webhook_invoice_enable = fields.Boolean(
        string="Enviar webhook al emitir factura",
        help="Si está activo (y los webhooks salientes encendidos), al emitir una factura de cliente se encola un evento invoice_posted.",
        default=True,
    )
    lida_webhook_payment_enable = fields.Boolean(
        string="Enviar webhook al registrar pago",
        help="Si está activo (y los webhooks salientes encendidos), al confirmar un pago de cliente se encola un evento payment_posted.",
        default=True,
    )

    lida_endpoint_quote_enable = fields.Boolean(
        string="Habilitar POST /api/quote",
        help="Permite a sistemas externos crear cotizaciones. Deshabilitado, el endpoint responde 403.",
        default=True,
    )
    lida_endpoint_invoice_enable = fields.Boolean(
        string="Habilitar POST /api/invoice",
        help="Permite a sistemas externos crear facturas de cliente. Deshabilitado, el endpoint responde 403.",
        default=True,
    )
    lida_endpoint_payment_enable = fields.Boolean(
        string="Habilitar POST /api/payment",
        help="Permite a sistemas externos registrar pagos de cliente. Deshabilitado, el endpoint responde 403.",
        default=True,
    )

    def get_values(self):
        res = super().get_values()
        ICP = self.env["ir.config_parameter"].sudo()
        for field_name, param in TRUE_DEFAULT_PARAMS.items():
            res[field_name] = ICP.get_param(param, "1") != "0"
        return res

    def set_values(self):
        super().set_values()
        ICP = self.env["ir.config_parameter"].sudo()
        for field_name, param in TRUE_DEFAULT_PARAMS.items():
            ICP.set_param(param, "1" if self[field_name] else "0")
