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

    is_debit = fields.Boolean(computed='_computed_is_debit')

    @api.depends('l10n_latam_document_type_id')
    def _computed_is_debit(self):
        for move in self:
            move.is_debit = move.l10n_latam_document_type_id.internal_type == 'debit_note'

    @api.depends('journal_id')
    def _compute_is_debit_journal(self):
        for move in self:
            move.is_debit_journal = True

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

    def action_debit_note_button(self):
        action = ""
        for picking in self:
            action = picking.env.ref('account_debit_note.action_view_account_move_debit').read()[0]
        return action
