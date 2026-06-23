import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ve_invoice_first_document_number = fields.Integer("Número de la primera factura")
    l10n_ve_credit_note_first_document_number = fields.Integer("Número de la primera nota de crédito")
    l10n_ve_debit_note_first_document_number = fields.Integer("Número de la primera  nota de débito")

    @api.onchange('type', 'l10n_latam_use_documents')
    def _onchange_journal_type(self):
        if self.type != 'sale':
            self.l10n_ve_invoice_first_document_number = False
            self.l10n_ve_credit_note_first_document_number = False
            self.l10n_ve_debit_note_first_document_number = False
        else:
            self.l10n_ve_invoice_first_document_number = self.l10n_ve_invoice_first_document_number or 1
            self.l10n_ve_credit_note_first_document_number = self.l10n_ve_credit_note_first_document_number or 1
            self.l10n_ve_debit_note_first_document_number = self.l10n_ve_debit_note_first_document_number or 1
