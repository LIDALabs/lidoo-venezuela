import logging

from odoo import _, fields, models, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ve_invoice_first_document_number = fields.Integer("Número de la primera factura")
    l10n_ve_credit_note_first_document_number = fields.Integer("Número de la primera nota de crédito")
    l10n_ve_debit_note_first_document_number = fields.Integer("Número de la primera  nota de débito")

    @api.onchange('type')
    def _onchange_journal_type(self):
        if self.type != 'sale':
            self.l10n_ve_invoice_first_document_number = False
            self.l10n_ve_credit_note_first_document_number = False
            self.l10n_ve_debit_note_first_document_number = False
        else:
            self.l10n_ve_invoice_first_document_number = self.l10n_ve_invoice_first_document_number or 1
            self.l10n_ve_credit_note_first_document_number = self.l10n_ve_credit_note_first_document_number or 1
            self.l10n_ve_debit_note_first_document_number = self.l10n_ve_debit_note_first_document_number or 1
            
    def write(self, vals):
        protected_fields = ('type', 'l10n_latam_use_documents', 'is_contingency', 'series_correlative_sequence_id')
        fields_to_check = [field for field in protected_fields if field in vals]

        if fields_to_check:
            self._cr.execute("SELECT DISTINCT(journal_id) FROM account_move WHERE posted_before = True")
            res = self._cr.fetchall()
            journal_with_entry_ids = [journal_id for journal_id, in res]

            for journal in self:
                if (
                    journal.company_id.account_fiscal_country_id.code != "VE"
                    or journal.type not in ['sale', 'purchase']
                    or journal.id not in journal_with_entry_ids
                ):
                    continue

                for field in fields_to_check:
                    # Wouldn't work if there was a relational field, as we would compare an id with a recordset.
                    if vals[field] != journal[field]:
                        raise UserError(_("You can not change %s journal's configuration if it already has validated invoices", journal.name))

        return super().write(vals)
