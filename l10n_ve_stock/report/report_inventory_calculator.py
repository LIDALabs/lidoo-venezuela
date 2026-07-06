from odoo import models
from odoo.tools import format_amount


class ReportInventoryCalculator(models.AbstractModel):
    _name = "report.l10n_ve_stock.report_inventory_calculator"
    _description = "Reporte PDF de Calculadora de Inventario"

    def _get_report_values(self, docids, data=None):
        docs = self.env["inventory.calculator"].browse(docids)
        return {
            "doc_ids": docids,
            "docs": docs,
            "company": docs[:1].company_id,
            "format_amount": lambda doc, amount: format_amount(
                self.env, amount, doc.currency_id
            ),
        }
