from odoo import fields, models
from datetime import datetime
from dateutil.relativedelta import relativedelta


class InvoicePaymentsReportWizard(models.TransientModel):
    _name = "invoice.payments.report.wizard"
    _description = "Asistente para Reporte de pagos de facturas"
    _check_company_auto = True

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company.id)
    date_from = fields.Date("Fecha", required=True, default=datetime.today())
    # date_to = fields.Date(
    #     required=True, default=datetime.today()
    # )

    def action_print(self):
        return self.ref("l10n_ve_invoice_extensions.invoice_payments_report").report_action(
            self
        )
