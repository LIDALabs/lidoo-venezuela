from odoo import fields, models


class LidooAnalyticsLog(models.Model):
    _name = "lidoo.analytics.log"
    _description = "Analytics Transmission Log"
    _order = "send_date desc"

    send_date = fields.Datetime(
        string="Send Date",
        default=fields.Datetime.now,
        readonly=True,
    )
    status = fields.Selection(
        [("success", "Success"), ("error", "Error")],
        string="Status",
        readonly=True,
    )
    payload_hash = fields.Char(
        string="Payload Hash",
        readonly=True,
        help="SHA-256 hash of the transmitted payload.",
    )
    error_message = fields.Text(
        string="Error Message",
        readonly=True,
    )
