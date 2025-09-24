from datetime import datetime

from odoo import api, fields, models
from odoo.tools.misc import formatLang
from odoo.exceptions import UserError


class InvoicePaymentsReport(models.AbstractModel):
    _name = 'report.l10n_ve_invoice_extensions.report_invoice_payments'

    def _get_report_values(self, docids, data=None):
        # get the report action back as we will need its data
        report = self.env['ir.actions.report']._get_report_from_name('module.report_name')

        report_date = False
        wizard_instance = self.env['invoice.payments.report.wizard'].browse(docids)
        if wizard_instance:
            report_date = wizard_instance.date_from
        if not report_date:
            report_date = self.env.context.get("invoice_payments_report_date_from")
        if not report_date:
            report_date = datetime.today()
        report_date_formatted = report_date.strftime('%Y-%m-%d')
        obj = self.env['account.move'].search([
            ('move_type', 'in', ['out_invoice', 'out_refund', 'out_receipt']),
            ('state', '=', 'posted'),
            ('date', '=', report_date),
        ])

        invoice_payments_data = {}
        for invoice in obj:
            invoice_payments_data[invoice.id] = {
                'payments': [],
                'total_payments': 0.0,
            }

            if not invoice.invoice_payments_widget:
                continue

            payments = invoice.invoice_payments_widget.get('content', False)
            for payment in payments:
                payment_id = payment.get('account_payment_id', False)
                if not payment_id:
                    continue
                payment_record = self.env['account.payment'].browse([payment_id])
                invoice_payments_data[invoice.id]['payments'].append({
                    'id': payment_record.id,
                    'reference': " ".join(filter(lambda x: x, [payment_record.ref, payment_record.concept])),
                    'name': payment_record.name,
                    'payment_method': f"{payment_record.journal_id.name} / {payment_record.payment_method_line_id.name}",
                    'amount': formatLang(
                        self.env, payment_record.amount_company_currency_signed, currency_obj=payment_record.currency_id
                    ),
                    'amount_original': formatLang(
                        self.env, payment_record.amount, currency_obj=payment_record.currency_id
                    ),
                    'exchange_rate': payment_record.foreign_rate,
                    'is_igtf': payment_record.is_igtf_on_foreign_exchange,
                    'date': payment_record.date,
                })
                invoice_payments_data[invoice.id]['total_payments'] += payment_record.amount

        return {
            'invoices': obj,
            'invoice_payments_data': invoice_payments_data,
            'report_date': report_date,
            'report_date_formatted': report_date_formatted,
        }
