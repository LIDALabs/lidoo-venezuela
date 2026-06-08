from datetime import datetime

from odoo import models
from odoo.tools.misc import formatLang


class InvoicePaymentsReport(models.AbstractModel):
    _name = 'report.l10n_ve_invoice_extensions.report_invoice_payments'

    def _get_report_values(self, docids, data=None):
        show_details = self.env.company.report_show_invoice_details

        report_date = False
        wizard_instance = self.env['invoice.payments.report.wizard'].browse(docids)
        if wizard_instance:
            report_date = wizard_instance.date_from
        if not report_date:
            report_date = self.env.context.get("invoice_payments_report_date_from")
        if not report_date:
            report_date = datetime.today()
        report_date_formatted = report_date.strftime('%Y-%m-%d')

        invoices = self.env['account.move'].search([
            ('move_type', 'in', ['out_invoice', 'out_refund', 'out_receipt']),
            ('state', '=', 'posted'),
            ('date', '=', report_date),
        ])

        # Company data
        company = self.env.company
        company_name = company.name
        company_rif = company.l10n_ve_vat or company.vat or ''
        currency_bs = company.currency_id

        # Totals
        total_bs = 0.0
        invoice_payments_data = {}
        for invoice in invoices:
            total_bs += invoice.amount_total_signed
            invoice_payments_data[invoice.id] = {
                'payments': [],
                'total_payments': 0.0,
                'items': [],
                'show_details': show_details,
            }

            if show_details:
                for line in invoice.invoice_line_ids:
                    if line.display_type in ('line_section', 'line_note'):
                        continue

                    invoice_payments_data[invoice.id]['items'].append({
                        'product': line.product_id.display_name or line.name,
                        'description': line.name,
                        'quantity': line.quantity,
                        'price_unit': formatLang(self.env, line.price_unit, currency_obj=invoice.currency_id),
                        'subtotal': formatLang(self.env, line.price_subtotal, currency_obj=invoice.currency_id),
                        'iva_amount': formatLang(self.env, line.price_total - line.price_subtotal, currency_obj=invoice.currency_id),
                    })

            if not invoice.invoice_payments_widget:
                continue

            payments = invoice.invoice_payments_widget.get('content', False)
            for payment in payments:
                payment_id = payment.get('account_payment_id', False)
                if not payment_id:
                    continue
                # Usar el monto reconciliado del widget, NO el monto total del payment record
                reconciled_amount = payment.get('amount', 0.0)
                payment_record = self.env['account.payment'].browse([payment_id])
                invoice_payments_data[invoice.id]['payments'].append({
                    'id': payment_record.id,
                    'reference': " ".join(filter(lambda x: x, [payment_record.ref, payment_record.concept])),
                    'name': payment_record.name,
                    'payment_method': f"{payment_record.journal_id.name} / {payment_record.payment_method_line_id.name}",
                    'amount': formatLang(
                        self.env, reconciled_amount, currency_obj=payment_record.currency_id
                    ),
                    'amount_original': formatLang(
                        self.env, reconciled_amount, currency_obj=payment_record.currency_id
                    ),
                    'exchange_rate': payment_record.foreign_rate,
                    'is_igtf': payment_record.is_igtf_on_foreign_exchange,
                    'date': payment_record.date,
                })
                invoice_payments_data[invoice.id]['total_payments'] += reconciled_amount

        # Exchange rate: how many Bs per 1 USD
        foreign_currency = company.currency_foreign_id
        rate_usd = 0.0
        try:
            if foreign_currency:
                rate_data = self.env['res.currency.rate'].compute_rate(foreign_currency.id, report_date)
                rate_usd = rate_data.get('foreign_rate', 0.0) or 0.0
        except Exception:
            rate_usd = 0.0

        total_usd = total_bs / rate_usd if rate_usd else 0.0

        # Format totals
        total_bs_fmt = formatLang(self.env, total_bs, currency_obj=currency_bs)
        total_usd_fmt = formatLang(self.env, total_usd, currency_obj=foreign_currency) if rate_usd else ''

        return {
            'invoices': invoices,
            'invoice_payments_data': invoice_payments_data,
            'report_date': report_date,
            'report_date_formatted': report_date_formatted,
            'company_name': company_name,
            'company_rif': company_rif,
            'total_bs': total_bs_fmt,
            'total_usd': total_usd_fmt,
            'rate_usd': rate_usd,
        }
