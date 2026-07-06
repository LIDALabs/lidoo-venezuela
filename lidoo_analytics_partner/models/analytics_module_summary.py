from odoo import fields, models, tools


class LidooAnalyticsModuleSummary(models.Model):
    _name = "lidoo.analytics.module.summary"
    _description = "Resumen de módulos"
    _auto = False
    _order = "name asc"

    name = fields.Char(
        string="Módulo",
        readonly=True,
    )
    client_count = fields.Integer(
        string="Clientes",
        readonly=True,
    )
    last_version = fields.Char(
        string="Última versión",
        readonly=True,
    )
    last_report_date = fields.Datetime(
        string="Último reporte",
        readonly=True,
    )
    is_custom = fields.Boolean(
        string="Custom",
        readonly=True,
    )

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE OR REPLACE VIEW lidoo_analytics_module_summary AS (
                SELECT
                    MIN(id) AS id,
                    name,
                    COUNT(DISTINCT client_id) AS client_count,
                    (ARRAY_AGG(version ORDER BY report_date DESC))[1] AS last_version,
                    MAX(report_date) AS last_report_date,
                    BOOL_OR(is_custom) AS is_custom
                FROM lidoo_analytics_report_modules
                GROUP BY name
            )
        """)

    def action_view_clients(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Clientes con %s" % self.name,
            "res_model": "lidoo.analytics.report.modules.latest",
            "view_mode": "tree",
            "search_view_id": self.env.ref(
                "lidoo_analytics_partner.view_lidoo_analytics_report_modules_latest_search"
            ).id,
            "domain": [("name", "=", self.name)],
            "context": {
                "create": False,
                "edit": False,
                "delete": False,
            },
            "target": "current",
        }
