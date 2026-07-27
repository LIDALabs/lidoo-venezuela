# -*- coding: utf-8 -*-
import json
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        """Post payments and enqueue outbound webhook events."""
        res = super().action_post()

        Event = self.env["lida_integration_api.webhook.event"].sudo()
        settings = Event._get_webhook_settings()
        # Master switch + toggle específico de pagos.
        if not settings.get("enabled") or not settings.get("payment_enabled"):
            return res

        for payment in self:
            if payment.payment_type != "inbound":
                continue
            # Only notify payments that were actually posted and numbered.
            if payment.state != "posted" or not payment.name or payment.name == "/":
                continue

            reference = f"account.payment,{payment.id}"
            if Event._has_recent_event("payment_posted", reference):
                _logger.info(
                    "Skipping duplicated payment_posted webhook for %s", reference
                )
                continue

            # A webhook failure must never roll back the posting itself.
            try:
                payload = payment._lida_build_payment_payload()
                Event.enqueue(
                    event_type="payment_posted",
                    payload=json.dumps(payload),
                    reference=reference,
                )
            except Exception:
                _logger.exception(
                    "Could not enqueue payment_posted webhook for %s", reference
                )

        return res

    def _lida_build_payment_payload(self):
        """Build the canonical data dict for an inbound payment.

        Single source of truth shared by the outbound webhook (payment_posted)
        and the synchronous /api/payment response.
        """
        self.ensure_one()
        payment = self
        partner = payment.partner_id
        foreign_currency = payment.company_id.currency_foreign_id

        foreign_amount = None
        if foreign_currency:
            if payment.currency_id == foreign_currency:
                foreign_amount = round(payment.amount, 2)
            elif payment.foreign_inverse_rate:
                # foreign_inverse_rate (l10n_ve_accountant) is the factor that
                # converts the payment amount into the alternate currency,
                # using the rate of the payment date.
                foreign_amount = round(payment.amount * payment.foreign_inverse_rate, 2)
            else:
                foreign_amount = round(
                    payment.currency_id._convert(
                        payment.amount,
                        foreign_currency,
                        payment.company_id,
                        payment.date or fields.Date.context_today(payment),
                    ),
                    2,
                )

        # La conciliación con facturas ocurre después de action_post (tanto en
        # la API como en el wizard de la UI), así que estos campos se terminan
        # de completar al momento del envío (ver _refresh_payload).
        invoices = payment.reconciled_invoice_ids
        return {
            "event": "payment_posted",
            # "api" cuando el posteo vino de /api/payment; "odoo" desde la UI.
            "source": "api" if self.env.context.get("lida_api_origin") else "odoo",
            "is_advance": not invoices,
            "invoice_ids": invoices.ids,
            "invoice_numbers": invoices.mapped("name"),
            "payment_id": payment.id,
            "payment_name": payment.name,
            "rif": f"{partner.prefix_vat or ''}{partner.vat or ''}".strip(),
            "amount": round(payment.amount, 2),
            "currency": payment.currency_id.name,
            "foreign_amount": foreign_amount,
            "foreign_currency": foreign_currency.name if foreign_currency else None,
            "payment_reference": payment.ref or "",
            "bank_reference": payment.concept or "",
            "date": str(payment.date) if payment.date else None,
            "journal_code": payment.journal_id.code,
            "payment_method_code": payment.payment_method_line_id.payment_method_id.code or "",
        }
