from odoo import api, models


class NetAmountReport(models.AbstractModel):
    _name='report.l10n_ve_product_flow_metrics.report_metrics_template'
    _description='Flow Metrics Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs= self.env['flow.metrics'].browse(docids).sudo()

        return {
            'doc_ids': docids,
            'doc_model': 'flow.metrics',
            'docs': docs,
        }