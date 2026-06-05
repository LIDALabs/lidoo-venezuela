from odoo import fields, models


class LidooAnalyticsReportModules(models.Model):
    _name="lidoo.analytics.report.modules"
    _description="Installed Modules"
    _order="report_id desc"


    report_id=fields.Many2one(
        "lidoo.analytics.report",
        string="Report",
        required=True,
        ondelete="cascade",
    )

    name=fields.Char(
        string="Module", 
        required=True,
    )
    version=fields.Char(
        string="Version"
    )