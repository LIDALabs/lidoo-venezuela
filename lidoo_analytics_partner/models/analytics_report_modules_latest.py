from odoo import fields, models, tools


class LidooAnalyticsReportModulesLatest(models.Model):
    _name = "lidoo.analytics.report.modules.latest"
    _description = "Última versión de módulo por cliente"
    _auto = False
    _order = "client_id asc, name asc"

    report_id = fields.Many2one(
        "lidoo.analytics.report",
        string="Reporte",
        readonly=True,
    )
    client_id = fields.Many2one(
        "lidoo.analytics.client",
        string="Cliente",
        readonly=True,
    )
    report_date = fields.Datetime(
        string="Fecha del reporte",
        readonly=True,
    )
    name = fields.Char(
        string="Módulo",
        readonly=True,
    )
    version = fields.Char(
        string="Versión",
        readonly=True,
    )
    is_custom = fields.Boolean(
        string="Custom",
        readonly=True,
    )
    author = fields.Char(
        string="Autor",
        readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW lidoo_analytics_report_modules_latest AS (
                SELECT DISTINCT ON (client_id, name)
                    id,
                    report_id,
                    client_id,
                    report_date,
                    name,
                    version,
                    is_custom,
                    author
                FROM lidoo_analytics_report_modules
                ORDER BY client_id, name, report_date DESC
            )
        """)
