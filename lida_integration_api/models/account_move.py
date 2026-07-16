# -*- coding: utf-8 -*-
import json
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        """Post invoices and enqueue outbound webhook events."""
        res = super().action_post()

        Event = self.env["lida_integration_api.webhook.event"].sudo()
        settings = Event._get_webhook_settings()
        # Master switch + toggle específico de facturas.
        if not settings.get("enabled") or not settings.get("invoice_enabled"):
            return res

        for move in self:
            if not move.is_invoice() or move.move_type != "out_invoice":
                continue
            # Only notify invoices that were actually posted and numbered.
            # action_post can be reached with draft data (e.g. double click,
            # flows that call it more than once); those must not emit events.
            if move.state != "posted" or not move.name or move.name == "/":
                continue

            reference = f"account.move,{move.id}"
            if Event._has_recent_event("invoice_posted", reference):
                _logger.info(
                    "Skipping duplicated invoice_posted webhook for %s", reference
                )
                continue

            # A webhook failure must never roll back the posting itself.
            try:
                payload = move._lida_build_invoice_payload()
                Event.enqueue(
                    event_type="invoice_posted",
                    payload=json.dumps(payload),
                    reference=reference,
                )
            except Exception:
                _logger.exception(
                    "Could not enqueue invoice_posted webhook for %s", reference
                )

        return res

    def _lida_build_invoice_payload(self):
        """Build the canonical data dict for a customer invoice.

        Single source of truth shared by the outbound webhook (invoice_posted)
        and the synchronous /api/invoice response, so both carry the same
        fields (control_number, totals, foreign totals, lines, ...).
        """
        self.ensure_one()
        move = self
        lines = []
        for line in move.invoice_line_ids.filtered(lambda l: l.display_type == "product"):
            lines.append(
                {
                    "sku": line.product_id.default_code or "",
                    "name": line.name,
                    "quantity": line.quantity,
                    "price_unit": round(line.price_unit, 2),
                    "price_subtotal": round(line.price_subtotal, 2),
                }
            )

        foreign_currency = move.company_id.currency_foreign_id
        foreign_amount = None
        if foreign_currency:
            # foreign_amount_total is injected in tax_totals by l10n_ve_tax.
            try:
                tax_totals = move.tax_totals or {}
                raw = tax_totals.get("foreign_amount_total")
                if raw is not None:
                    foreign_amount = round(raw, 2)
            except Exception:
                _logger.exception(
                    "Could not read foreign totals for invoice %s", move.id
                )

        partner = move.partner_id
        return {
            "event": "invoice_posted",
            # "api" cuando el posteo vino de /api/invoice (permite al receptor
            # ignorar el eco de sus propias operaciones); "odoo" desde la UI.
            "source": "api" if self.env.context.get("lida_api_origin") else "odoo",
            "invoice_id": move.id,
            "invoice_number": move.name,
            "control_number": move.correlative or "",
            "rif": f"{partner.prefix_vat or ''}{partner.vat or ''}".strip(),
            "amount": round(move.amount_total, 2),
            "currency": move.currency_id.name,
            "foreign_amount": foreign_amount,
            "foreign_currency": foreign_currency.name if foreign_currency else None,
            "payment_reference": move.payment_reference or move.ref or "",
            "date": str(move.invoice_date) if move.invoice_date else None,
            "lines": lines,
        }
