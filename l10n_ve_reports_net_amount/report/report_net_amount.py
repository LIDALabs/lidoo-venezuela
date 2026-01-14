from odoo import api, models


class NetAmountReport(models.AbstractModel):
    _name='report.l10n_ve_reports_net_amount.report_net_amount_template'
    _description='Net Amount Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs= self.env['net.amount.result'].browse(docids).sudo()

        return {
            'doc_ids': docids,
            'doc_model': 'net.amount.result',
            'docs': docs,
        }