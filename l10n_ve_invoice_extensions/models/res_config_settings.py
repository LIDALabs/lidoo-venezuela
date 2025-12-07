import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_sales_invoicing_series = fields.Boolean(
        related="company_id.group_sales_invoicing_series",
        readonly=True,
        implied_group="l10n_ve_invoice.group_sales_invoicing_series",
    )

    report_show_invoice_details = fields.Boolean(
        related="company_id.report_show_invoice_details",
        readonly=False,
        string="Mostrar detalles (ítems) en reporte de Cierre Diario",
    )