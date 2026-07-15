from odoo import api, fields, models
from odoo.tools.misc import formatLang


class NetAmountReport(models.AbstractModel):
    _name='report.l10n_ve_product_flow_metrics.report_metrics_template'
    _description='Flow Metrics Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs= self.env['flow.metrics'].browse(docids).sudo()

        company = self.env.company
        currency_bs = company.currency_id
        foreign_currency = company.currency_foreign_id

        rate_usd = 0.0
        if foreign_currency:
            try:
                report_date = docs[0].date_to if docs else fields.Date.today()
                rate_data = self.env['res.currency.rate'].compute_rate(
                    foreign_currency.id, report_date
                )
                rate_usd = rate_data.get('foreign_rate', 0.0) or 0.0
            except Exception:
                rate_usd = 0.0

        docs_data = []
        for doc in docs:
            docs_data.append({
                'product_id': doc.product_id,
                'product_selection': doc.product_selection,
                'date_from': doc.date_from,
                'date_to': doc.date_to,
                'qty_purchased': doc.qty_purchased,
                'qty_purchased_return': doc.qty_purchased_return,
                'qty_purchased_net': doc.qty_purchased_net,
                'qty_sold': doc.qty_sold,
                'qty_sold_return': doc.qty_sold_return,
                'qty_sold_net': doc.qty_sold_net,
                'product_uom_id': doc.product_uom_id,
                'purchase_price_ves': formatLang(self.env, doc.standard_price_ves, currency_obj=currency_bs),
                'purchase_price_usd': formatLang(self.env, doc.standard_price_usd, currency_obj=foreign_currency) if foreign_currency and rate_usd else '-',
                'sale_price_ves': formatLang(self.env, doc.sale_price_ves, currency_obj=currency_bs),
                'sale_price_usd': formatLang(self.env, doc.sale_price_usd, currency_obj=foreign_currency) if foreign_currency and rate_usd else '-',
                'total_purchased_ves': formatLang(self.env, doc.total_purchased_ves, currency_obj=currency_bs),
                'total_purchased_usd': formatLang(self.env, doc.total_purchased_usd, currency_obj=foreign_currency) if foreign_currency and rate_usd else '-',
                'total_sold_ves': formatLang(self.env, doc.total_sold_ves, currency_obj=currency_bs),
                'total_sold_usd': formatLang(self.env, doc.total_sold_usd, currency_obj=foreign_currency) if foreign_currency and rate_usd else '-',
            })

        return {
            'doc_ids': docids,
            'doc_model': 'flow.metrics',
            'docs': docs,
            'docs_data': docs_data,
            'rate_usd': rate_usd,
        }