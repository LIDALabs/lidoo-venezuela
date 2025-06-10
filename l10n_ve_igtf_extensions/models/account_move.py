# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_round

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    amount_subject_to_igtf = fields.Monetary(
        string="Monto pagado en USD",
        help="Monto pagado en divisa sujeto a IGTF",
        copy=False,
        currency_field='foreign_currency_id'
    )
    amount_untaxed_in_usd = fields.Monetary(
        string="Subtotal en USD",
        store=False,
        currency_field='foreign_currency_id',
        compute='_compute_amount_untaxed_in_usd'
    )

    bi_igtf = fields.Monetary(tracking=True, store=True, readonly=False, compute='_compute_bi_igtf')

    bi_igtf_payed = fields.Monetary(string="Total pagado sujeto a IGTF", help="IGTF", copy=False)
    bi_igtf_difference = fields.Monetary(
        string="Diferencia entre pagado y gravado",
        help="Diferencia entre el monto de IGTF pagado y gravado",
        copy=False,
        compute="_compute_bi_igtf_difference_with_manual")

    @api.depends('amount_untaxed', 'amount_subject_to_igtf', 'foreign_rate', 'foreign_inverse_rate')
    def _compute_bi_igtf(self):
        for move in self:
            # This functions runs when the localization is being installed. At that point, there might not be a foreign currency configured.
            if not move.foreign_currency_id:
                continue
            move.bi_igtf = float_round(min(move.amount_untaxed, move.amount_subject_to_igtf * move.foreign_rate), precision_rounding=move.currency_id.rounding)
            move.amount_subject_to_igtf = float_round(move.bi_igtf * move.foreign_inverse_rate, precision_rounding=move.foreign_currency_id.rounding)

    @api.depends('amount_untaxed', 'foreign_inverse_rate')
    def _compute_amount_untaxed_in_usd(self):
        for record in self:
            record.amount_untaxed_in_usd = record.amount_untaxed * record.foreign_inverse_rate

    @api.depends('bi_igtf', 'bi_igtf_payed')
    def _compute_bi_igtf_difference_with_manual(self):
        for record in self:
            record.bi_igtf_difference = record.bi_igtf_payed - record.bi_igtf

    def recalculate_bi_igtf(self, line_id=None, initial_residual=0.0):
        """Calcula el total pagado sujeto a IGTF en lugar del gravado"""
        for record in self:
            if not record.invoice_payments_widget:
                record.bi_igtf_payed = 0
                continue

            payments = record.invoice_payments_widget.get("content", False)
            amount = 0
            if line_id:
                line = self.env["account.move.line"].browse([line_id])
                payment_id = line.move_id.payment_id
                if payment_id and payment_id.is_igtf_on_foreign_exchange:
                    payment_id = line.move_id.payment_id
                    bi_igtf_payed = payment_id.get_bi_igtf()
                    if initial_residual < bi_igtf_payed:
                        record.bi_igtf_payed = initial_residual
                        continue
                    record.bi_igtf_payed += bi_igtf_payed
                    continue

            for payment in payments:
                payment_id = payment.get("account_payment_id", False)
                if not payment_id:
                    continue

                payment_id = record.env["account.payment"].browse([payment_id])
                if payment_id.is_igtf_on_foreign_exchange:
                    bi_igtf_payed = payment_id.get_bi_igtf()
                    if initial_residual < bi_igtf_payed:
                        record.bi_igtf_payed = initial_residual
                        continue
                    amount += bi_igtf_payed

            record.bi_igtf_payed = amount
