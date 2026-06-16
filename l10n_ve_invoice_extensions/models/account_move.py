import json
import logging
import re
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_date

_logger = logging.getLogger(__name__)

PREPRINTED_CORRELATIVE_PATTERN = re.compile('^\d{2}[-]\d{1,8}$')


class AccountMove(models.Model):
    _inherit = "account.move"

    is_debit = fields.Boolean(compute='_computed_is_debit')

    amount_subtotal = fields.Float(
        string="Subtotal",
        compute='_compute_total_custom',
        # store=True,
        digits='Account'
    )

    @api.depends('invoice_line_ids.price_subtotal')
    def _compute_total_custom(self):
        raw_data = self.env['account.move.line']._read_group(
            [('move_id', 'in', self.ids)],
            ['move_id'],
            ['price_subtotal:sum']
        )

        subtotal_data = {
            move.id: price_subtotal_sum
            for move, price_subtotal_sum in raw_data
        }

        for record in self:
            # total_acumulado = sum(line.price_subtotal for line in record.invoice_line_ids)
            record.amount_subtotal = subtotal_data.get(record.id, 0)

    def _is_manual_document_number(self):
        return self.journal_id.type == 'purchase' or self.is_contingency

    @api.depends('l10n_latam_document_type_id')
    def _computed_is_debit(self):
        for move in self:
            move.is_debit = move.l10n_latam_document_type_id.internal_type == 'debit_note'

    @api.depends('journal_id')
    def _compute_is_debit_journal(self):
        for move in self:
            move.is_debit_journal = move.journal_id.is_debit if move.journal_id else False

    def _get_invoice_reference_odoo_invoice(self):
        """ This computes the reference based on the Odoo format.
            We simply return the number of the invoice, defined on the journal
            sequence.
        """
        self.ensure_one()
        return self.name

    @api.depends('restrict_mode_hash_table', 'state', 'posted_before', 'move_type')
    def _compute_show_reset_to_draft_button(self):
        """ Controla visibilidad del botón reset-to-draft.
        - out_invoice/out_receipt: nunca mostrar si ya fue posteada.
        - out_refund posteada: solo mostrar para administradores. """
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.move_type in ('out_invoice', 'out_receipt') and move.posted_before:
                move.show_reset_to_draft_button = False
            if move.move_type == 'out_refund' and move.state == 'posted' and move.posted_before:
                if not self.env.user.has_group('base.group_erp_manager'):
                    move.show_reset_to_draft_button = False

    def button_draft(self):
        """ Restringe reset-to-draft de notas de crédito posteadas solo a administradores. """
        for move in self:
            if move.move_type == 'out_refund' and move.state == 'posted':
                if not self.env.user.has_group('base.group_erp_manager'):
                    raise UserError(_(
                        "Solo un administrador puede regresar una nota de crédito "
                        "contabilizada a borrador.\n"
                        "Por favor contacte a su administrador del sistema."
                    ))
        return super().button_draft()

    @api.model
    def get_sequence(self):
        """
        Allows the invoice to have both a generic sequence
        number or a specific one given certain conditions.

        Returns
        -------
            The next number from the sequence to be assigned.
        """

        self.ensure_one()
        sequence = self.journal_id.series_correlative_sequence_id

        if not sequence:
            raise UserError(_("The sale's series sequence must be in the selected journal."))

        correlative = sequence.next_by_id(sequence.id)

        if not PREPRINTED_CORRELATIVE_PATTERN.match(correlative):
            raise UserError(_("El número de control generado no cumple con el patrón secuencia '00-00000'"))

        return correlative
