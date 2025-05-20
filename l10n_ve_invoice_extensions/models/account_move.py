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

    @api.depends('l10n_latam_document_type_id')
    def _computed_is_debit(self):
        for move in self:
            move.is_debit = move.l10n_latam_document_type_id.internal_type == 'debit_note'

    @api.depends('journal_id')
    def _compute_is_debit_journal(self):
        for move in self:
            move.is_debit_journal = True

    def _get_invoice_reference_odoo_invoice(self):
        """ This computes the reference based on the Odoo format.
            We simply return the number of the invoice, defined on the journal
            sequence.
        """
        self.ensure_one()
        return self.name

    @api.depends('posted_before', 'move_type')
    def _compute_show_reset_to_draft_button(self):
        """ Previene que un movimiento sea regresado a  """
        super()._compute_show_reset_to_draft_button()
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund', 'out_receipt') and move.posted_before:
                move.show_reset_to_draft_button = False

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

    def _check_price_in_zero(self):
        for record in self.filtered(lambda x: x.move_type != 'entry'):
            for line in record.invoice_line_ids:
                if line.price_unit <= 0:
                    raise ValidationError(("Una factura no puede tener una linea con precio en cero"))
