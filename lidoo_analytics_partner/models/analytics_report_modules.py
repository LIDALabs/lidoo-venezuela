from odoo import fields, models


class LidooAnalyticsReportModules(models.Model):
    _name="lidoo.analytics.report.modules"
    _description="Módulos instalados"
    _order="report_id desc"


    report_id=fields.Many2one(
        "lidoo.analytics.report",
        string="Reporte",
        required=True,
        ondelete="cascade",
    )

    name=fields.Char(
        string="Módulo",
        required=True,
    )
    version=fields.Char(
        string="Versión"
    )
    author=fields.Char(
        string="Autor"
    )
    is_custom=fields.Boolean(
        string="Módulo custom",
        default=False,
    )

    client_id=fields.Many2one(
        related="report_id.client_id",
        string="Cliente",
        store=True,
        index=True,
    )
    report_date=fields.Datetime(
        related="report_id.report_date",
        string="Fecha del reporte",
        store=True,
    )