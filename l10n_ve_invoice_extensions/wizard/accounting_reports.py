import logging
from datetime import datetime
from io import BytesIO

import xlsxwriter
from dateutil.relativedelta import relativedelta
from odoo import _, fields, models
from odoo.exceptions import UserError
from xlsxwriter import utility

_logger = logging.getLogger(__name__)
INIT_LINES = 8


class AccountingReportsWizard(models.TransientModel):
    _inherit = "wizard.accounting.reports"

    # def _get_domain(self):
    #     """Modifica el dominio para utilizar invoice_date en lugar de invoice"""
    #     search_domain = []
    #     is_purchase = self.report == "purchase"

    #     search_domain += [("company_id", "=", self.company_id.id)]

    #     move_type = (
    #         ["out_invoice", "out_refund"]
    #         if not is_purchase
    #         else ["in_invoice", "in_refund", "in_debit"]
    #     )

    #     search_domain += [("invoice_date", ">=", self.date_from)]
    #     search_domain += [("invoice_date", "<=", self.date_to)]
    #     search_domain += [
    #         ("state", "in", ("posted", "cancel")),
    #         ("move_type", "in", move_type),
    #         ("correlative", "not in", ['/', False])
    #     ]

    #     return search_domain

    def _fields_sale_book_line(self, move, taxes):
        """Corrige número de factura afectada"""
        fields_sale_book_line = super()._fields_sale_book_line(move, taxes)

        number_invoice_affected = ""
        if move.debit_origin_id:
            number_invoice_affected = move.debit_origin_id.l10n_latam_document_number
        elif move.reversed_entry_id:
            number_invoice_affected = move.reversed_entry_id.l10n_latam_document_number

        fields_sale_book_line.update({
            'number_invoice_affected': number_invoice_affected
        })

        return fields_sale_book_line

    def _fields_purchase_book_line(self, move, taxes):
        """Corrige número de factura afectada"""
        fields_purchase_book_line = super()._fields_purchase_book_line(move, taxes)

        number_invoice_affected = ""
        if move.debit_origin_id:
            number_invoice_affected = move.debit_origin_id.l10n_latam_document_number
        elif move.reversed_entry_id:
            number_invoice_affected = move.reversed_entry_id.l10n_latam_document_number

        fields_purchase_book_line.update({
            'number_invoice_affected': number_invoice_affected
        })

        return fields_purchase_book_line

    def _determinate_type_for_move(self, move):
        """Corrige número de factura afectada"""
        move_type = move.move_type
        if move.debit_origin_id:
            if move.move_type == 'out_invoice':
                move_type = "out_debit"
            elif move.move_type == 'in_invoice':
                move_type = "in_debit"

        type_for_move = self._determinate_type(move_type)

        return type_for_move
    
