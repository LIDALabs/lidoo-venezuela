from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_ve_get_formatted_sequence(self, number=0):
        return "%s %08d" % (self.l10n_latam_document_type_id.doc_code_prefix, number)

    def _get_starting_sequence(self):
        """ If use documents then will create a new starting sequence using the document type code prefix and the
        journal document number with a 8 padding number """
        if self.journal_id.l10n_latam_use_documents and self.company_id.account_fiscal_country_id.code == "VE":
            if self.l10n_latam_document_type_id:
                return self._l10n_ve_get_formatted_sequence()
        return super()._get_starting_sequence()

    def _get_last_sequence(self, relaxed=False, with_prefix=None):
        last_sequence = super(AccountMove, self)._get_last_sequence(relaxed, with_prefix)

        if not last_sequence:
            set_seq = 0
            if self.l10n_latam_document_type_id.internal_type == 'invoice':
                set_seq = int(self.journal_id.l10n_ve_invoice_first_document_number)
            elif self.l10n_latam_document_type_id.internal_type == 'credit_note':
                set_seq = int(self.journal_id.l10n_ve_credit_note_first_document_number)
            elif self.l10n_latam_document_type_id.internal_type == 'debit_note':
                set_seq = int(self.journal_id.l10n_ve_debit_note_first_document_number)

            set_seq = set_seq-1

            if set_seq > 0:
                return self._l10n_ve_get_formatted_sequence(set_seq)

        return last_sequence

    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
        if self.company_id.account_fiscal_country_id.code == "VE" and self.l10n_latam_use_documents:
            # where_string = where_string.replace('journal_id = %(journal_id)s AND', '')
            where_string += ' AND l10n_latam_document_type_id = %(l10n_latam_document_type_id)s AND company_id = %(company_id)s'

            param['company_id'] = self.company_id.id or False
            param['l10n_latam_document_type_id'] = self.l10n_latam_document_type_id.id or 0
        return where_string, param

    def button_cancel(self):
        """
        Limpia el número de documento al cancelar el movimiento para evitar que se ruede la numeración
        """
        res = super(AccountMove, self).button_cancel()
        for move in self:
            move.l10n_latam_document_number = False
        return res
