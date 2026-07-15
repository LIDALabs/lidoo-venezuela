from odoo import api, fields, models


class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'
    filter_enabled = fields.Boolean(string='Filter Enabled', compute='_compute_filter_enabled')

    @api.depends('journal_type')
    def _compute_filter_enabled(self):
        move = self.env['account.move'].browse(self.env.context.get('active_id'))
        config = move.company_id.auto_select_debit_note_journal
        for record in self:
            record.filter_enabled = config

    def _prepare_default_values(self, move):
        """Hereda los términos de pago de la factura origen al crear la nota de débito."""
        default_values = super()._prepare_default_values(move)
        default_values['invoice_payment_term_id'] = move.invoice_payment_term_id.id
        return default_values
