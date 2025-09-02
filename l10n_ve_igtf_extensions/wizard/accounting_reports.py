import logging
from datetime import datetime
from io import BytesIO

import xlsxwriter
from dateutil.relativedelta import relativedelta
from odoo import _, fields, models
from odoo.fields import float_round
from odoo.exceptions import UserError
from xlsxwriter import utility

_logger = logging.getLogger(__name__)
INIT_LINES = 8


class AccountingReportsWizard(models.TransientModel):
    _inherit = "wizard.accounting.reports"

    def _fields_sale_book_line(self, move, taxes):
        fields_sale_book_line = super()._fields_sale_book_line(move, taxes)

        multiplier = -1 if move.move_type == "out_refund" else 1

        igtf_totals = move.tax_totals.get('igtf', {})

        fields_sale_book_line.update({
            'igtf_aliquot': float_round(move.company_id.igtf_percentage / 100, 2),
            'igtf_base_amount': igtf_totals.get('igtf_base_amount', 0) * multiplier,
            'igtf_amount': igtf_totals.get('igtf_amount', 0) * multiplier,
            'foreign_igtf_base_amount': igtf_totals.get('foreign_igtf_base_amount', 0) * multiplier,
            'foreign_igtf_amount': igtf_totals.get('foreign_igtf_amount', 0) * multiplier,
        })

        return fields_sale_book_line

    def _fields_purchase_book_line(self, move, taxes):
        fields_purchase_book_line = super()._fields_purchase_book_line(move, taxes)

        multiplier = -1 if move.move_type == "in_refund" else 1

        igtf_totals = move.tax_totals.get('igtf', {})

        fields_purchase_book_line.update({
            'igtf_aliquot': float_round(move.company_id.igtf_percentage / 100, 2),
            'igtf_base_amount': igtf_totals.get('igtf_base_amount', 0) * multiplier,
            'igtf_amount': igtf_totals.get('igtf_amount', 0) * multiplier,
            'foreign_igtf_base_amount': igtf_totals.get('foreign_igtf_base_amount', 0) * multiplier,
            'foreign_igtf_amount': igtf_totals.get('foreign_igtf_amount', 0) * multiplier,
        })

        return fields_purchase_book_line
    

    def sale_book_fields(self):
        sale_book_fields = super().sale_book_fields()

        igtf_percent = self.env.company.igtf_percentage

        sale_book_fields.extend([
            {
                "name": f"Base imponible IGTF ({igtf_percent}%)",
                "field": "igtf_base_amount",
                "format": "number",
                "size": 15,
            },
            {
                "name": f"Alícuota IGTF ({igtf_percent}%)",
                "field": "igtf_aliquot",
                "format": "percent",
                "size": 15,
            },
            {
                "name": f"IGTF {igtf_percent}%",
                "field": "igtf_amount",
                "format": "number",
            },
        ])

        return sale_book_fields

    def purchase_book_fields(self):
        purchase_book_fields = super().purchase_book_fields()

        igtf_percent = self.env.company.igtf_percentage

        purchase_book_fields.extend([
            {
                "name": f"Base imponible IGTF ({igtf_percent}%)",
                "field": "igtf_base_amount",
                "format": "number",
                "size": 15,
            },
            {
                "name": f"Alícuota IGTF ({igtf_percent}%)",
                "field": "igtf_aliquot",
                "format": "percent",
                "size": 15,
            },
            {
                "name": f"IGTF {igtf_percent}%",
                "field": "igtf_amount",
                "format": "number",
            },
        ])

        return purchase_book_fields
    

    def _resume_sale_book_fields(self, moves):
        resume_sale_book_fields = super()._resume_sale_book_fields(moves)

        vef_base = self.company_id.currency_id.id == self.env.ref("base.VEF").id

        if vef_base:
            field_base, field_amount = ("igtf_base_amount", "igtf_amount")
        else:
            field_base, field_amount = ("foreign_igtf_base_amount", "foreign_igtf_amount")

        igtf_debit_base = 0.0
        igtf_debit_amount = 0.0
        igtf_credit_base = 0.0
        igtf_credit_amount = 0.0

        for move in moves:
            igtf_totals = move.tax_totals.get('igtf', {'apply_igtf': False})
            if not igtf_totals.get('apply_igtf', False):
                continue

            if move.move_type in ["out_refund", "in_refund"]:
                igtf_credit_base -= igtf_totals.get(field_base)
                igtf_credit_amount -= igtf_totals.get(field_amount)
            else: 
                igtf_debit_base += igtf_totals.get(field_base)
                igtf_debit_amount += igtf_totals.get(field_amount)
            

        resume_sale_book_fields.extend([
            {
                "name": "Pagos recibidos Gravados por IGTF",
                "format": "number",
                "values": [
                    igtf_debit_base,
                    igtf_debit_amount,
                    igtf_credit_base,
                    igtf_credit_amount,
                    0.0,
                    0.0,
                    # igtf_debit_base - igtf_credit_base,
                    # igtf_debit_amount - igtf_credit_amount,
                ],
            }
        ])

        return resume_sale_book_fields
    

    def _resume_purchase_book_fields(self, moves):
        resume_purchase_book_fields = super()._resume_purchase_book_fields(moves)

        vef_base = self.company_id.currency_id.id == self.env.ref("base.VEF").id

        if vef_base:
            field_base, field_amount = ("igtf_base_amount", "igtf_amount")
        else:
            field_base, field_amount = ("foreign_igtf_base_amount", "foreign_igtf_amount")

        igtf_debit_base = 0.0
        igtf_debit_amount = 0.0
        igtf_credit_base = 0.0
        igtf_credit_amount = 0.0

        for move in moves:
            igtf_totals = move.tax_totals.get('igtf', {'apply_igtf': False})
            if not igtf_totals.get('apply_igtf', False):
                continue

            if move.move_type in ["out_refund", "in_refund"]:
                igtf_credit_base -= igtf_totals.get(field_base)
                igtf_credit_amount -= igtf_totals.get(field_amount)
            else: 
                igtf_debit_base += igtf_totals.get(field_base)
                igtf_debit_amount += igtf_totals.get(field_amount)
            

        resume_purchase_book_fields.extend([
            {
                "name": "Pagos emitidos Gravados por IGTF",
                "format": "number",
                "values": [
                    igtf_debit_base,
                    igtf_debit_amount,
                    igtf_credit_base,
                    igtf_credit_amount,
                    0.0,
                    0.0,
                    # igtf_debit_base - igtf_credit_base,
                    # igtf_debit_amount - igtf_credit_amount,
                ],
            }
        ])
        
        return resume_purchase_book_fields