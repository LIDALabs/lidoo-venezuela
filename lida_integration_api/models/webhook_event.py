# -*- coding: utf-8 -*-
import datetime
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class WebhookEvent(models.Model):
    _name = "lida_integration_api.webhook.event"
    _description = "Outbound Webhook Event"
    _order = "create_date desc, id desc"

    event_type = fields.Selection(
        selection=[
            ("invoice_posted", "Invoice Posted"),
            ("payment_posted", "Payment Posted"),
        ],
        string="Event Type",
        required=True,
        index=True,
    )
    payload = fields.Text(string="Payload", required=True)
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("sent", "Sent"),
            ("failed", "Failed"),
        ],
        string="State",
        default="pending",
        required=True,
        index=True,
    )
    attempts = fields.Integer(string="Attempts", default=0)
    last_error = fields.Text(string="Last Error")
    next_attempt_at = fields.Datetime(
        string="Next Attempt At",
        default=fields.Datetime.now,
        index=True,
    )
    reference = fields.Char(
        string="Reference",
        help="Reference to the source record, e.g. account.move,123",
        index=True,
    )

    def _get_webhook_settings(self):
        """Return current webhook settings as a dict."""
        ICP = self.env["ir.config_parameter"].sudo()
        return {
            "enabled": ICP.get_param("lida_integration_api.webhook_enable", "False").lower()
            in ("true", "1", "yes"),
            # Toggles por tipo de evento (default habilitado). Gobernados por el
            # master "enabled": si el master está off, no se envía nada.
            "invoice_enabled": ICP.get_param(
                "lida_integration_api.webhook_invoice_enable", "1"
            ) != "0",
            "payment_enabled": ICP.get_param(
                "lida_integration_api.webhook_payment_enable", "1"
            ) != "0",
            "url": ICP.get_param("lida_integration_api.webhook_url", default=""),
            "secret": ICP.get_param("lida_integration_api.webhook_secret", default=""),
            "max_attempts": int(
                ICP.get_param("lida_integration_api.webhook_max_attempts", default="5")
            ),
        }

    @api.model
    def _has_recent_event(self, event_type, reference, minutes=5):
        """Return True if a pending/sent event for the same reference was
        created in the last ``minutes`` minutes.

        Used to avoid emitting duplicated webhooks when action_post is
        called more than once for the same record (double click, flows
        that re-post, etc.).
        """
        threshold = fields.Datetime.now() - datetime.timedelta(minutes=minutes)
        return bool(
            self.search_count(
                [
                    ("event_type", "=", event_type),
                    ("reference", "=", reference),
                    ("state", "in", ("pending", "sent")),
                    ("create_date", ">=", threshold),
                ],
                limit=1,
            )
        )

    @api.model
    def enqueue(self, event_type, payload, reference):
        """Create a pending webhook event and trigger immediate delivery.

        The HTTP POST still happens in the cron worker (never inside the
        posting transaction), but _trigger() wakes the cron right after
        commit instead of waiting for the 5-minute interval, which stays
        as a safety net for retries.
        """
        event = self.sudo().create(
            {
                "event_type": event_type,
                "payload": payload,
                "reference": reference,
                "state": "pending",
                "attempts": 0,
                "next_attempt_at": fields.Datetime.now(),
            }
        )
        cron = self.env.ref(
            "lida_integration_api.ir_cron_process_webhook_events",
            raise_if_not_found=False,
        )
        if cron:
            cron.sudo()._trigger()
        return event

    @api.model
    def _cron_process_pending_events(self):
        """Cron entry point: process pending webhook events."""
        settings = self._get_webhook_settings()
        if not settings["enabled"]:
            _logger.info("Webhook outbound disabled. Skipping.")
            return

        if not settings["url"]:
            _logger.warning("Webhook outbound enabled but URL not configured. Skipping.")
            return

        # Fetch pending events that are due for retry
        events = self.search(
            [
                ("state", "in", ("pending", "failed")),
                ("attempts", "<", settings["max_attempts"]),
                ("next_attempt_at", "<=", fields.Datetime.now()),
            ],
            order="create_date asc",
            limit=100,
        )

        for event in events:
            event._send(settings)

    def _refresh_payload(self):
        """Complete payment events with reconciliation data at send time.

        The invoice reconciliation happens after action_post (both in the
        API flow and in the UI register-payment wizard), so the linkage is
        unknown when the event is enqueued. By send time (post-commit,
        seconds later) it is final, so we refresh those fields here before
        signing and sending.
        """
        self.ensure_one()
        if self.event_type != "payment_posted" or not self.reference:
            return
        try:
            model, res_id = self.reference.split(",")
            if model != "account.payment":
                return
            payment = self.env["account.payment"].sudo().browse(int(res_id)).exists()
            if not payment:
                return
            payload = json.loads(self.payload)
            invoices = payment.reconciled_invoice_ids
            payload["is_advance"] = not invoices
            payload["invoice_ids"] = invoices.ids
            payload["invoice_numbers"] = invoices.mapped("name")
            self.payload = json.dumps(payload)
        except Exception:
            _logger.exception("Could not refresh payload for webhook event %s", self.id)

    def _send(self, settings=None):
        """Send a single webhook event via HTTP POST."""
        self.ensure_one()
        if settings is None:
            settings = self._get_webhook_settings()

        self._refresh_payload()

        import hashlib
        import hmac
        import json as _json
        import requests

        url = settings.get("url")
        secret = settings.get("secret", "")
        max_attempts = settings.get("max_attempts", 5)

        if not url:
            self.write(
                {
                    "state": "failed",
                    "last_error": "Webhook URL not configured",
                    "attempts": self.attempts + 1,
                }
            )
            return

        headers = {
            "Content-Type": "application/json",
        }
        if secret:
            signature = hmac.new(
                secret.encode("utf-8"),
                self.payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Lidoo-Signature"] = signature

        try:
            response = requests.post(
                url,
                data=self.payload.encode("utf-8"),
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            self.write(
                {
                    "state": "sent",
                    "attempts": self.attempts + 1,
                    "last_error": False,
                }
            )
            _logger.info(
                "Webhook event %s sent successfully (HTTP %s)",
                self.id,
                response.status_code,
            )
        except Exception as exc:
            attempts = self.attempts + 1
            if attempts >= max_attempts:
                state = "failed"
            else:
                state = "pending"

            # Exponential backoff: 2^attempts minutes
            next_attempt = fields.Datetime.now() + datetime.timedelta(minutes=2 ** attempts)
            self.write(
                {
                    "state": state,
                    "attempts": attempts,
                    "last_error": str(exc),
                    "next_attempt_at": next_attempt,
                }
            )
            _logger.warning(
                "Webhook event %s failed (attempt %s/%s): %s",
                self.id,
                attempts,
                max_attempts,
                exc,
            )

