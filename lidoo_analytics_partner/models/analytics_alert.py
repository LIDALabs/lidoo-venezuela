import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class LidooAnalyticsAlert(models.Model):
    _name = "lidoo.analytics.alert"
    _description = "Analytics Alert Rule"
    _order = "client_id, name"

    name = fields.Char(
        string="Alert Name",
        required=True,
    )
    client_id = fields.Many2one(
        "lidoo.analytics.client",
        string="Client",
        required=True,
        ondelete="cascade",
    )
    alert_type = fields.Selection(
        [
            ("no_report", "No Report Received"),
            ("version_below", "Version Below Minimum"),
            ("db_size_exceeded", "Database Size Exceeded"),
            ("user_count_change", "User Count Changed Significantly"),
        ],
        string="Alert Type",
        required=True,
    )
    threshold_value = fields.Float(
        string="Threshold",
        help=(
            "For 'No Report': hours without a report.\n"
            "For 'Version Below': not used (set minimum version in notes).\n"
            "For 'DB Size Exceeded': maximum size in GB.\n"
            "For 'User Count Change': percentage change threshold."
        ),
    )
    threshold_version = fields.Char(
        string="Minimum Version",
        help="Used with 'Version Below Minimum' alert type. E.g. '17.0'",
    )
    active = fields.Boolean(
        string="Active",
        default=True,
    )
    last_triggered = fields.Datetime(
        string="Last Triggered",
        readonly=True,
    )
    notes = fields.Text(
        string="Notes",
    )

    @api.model
    def _cron_check_alerts(self):
        """Check all active alert rules and trigger notifications."""
        alerts = self.search([("active", "=", True)])
        now = fields.Datetime.now()

        for alert in alerts:
            triggered = False

            if alert.alert_type == "no_report":
                triggered = self._check_no_report(alert, now)
            elif alert.alert_type == "version_below":
                triggered = self._check_version_below(alert)
            elif alert.alert_type == "db_size_exceeded":
                triggered = self._check_db_size_exceeded(alert)
            elif alert.alert_type == "user_count_change":
                triggered = self._check_user_count_change(alert)

            if triggered:
                alert.last_triggered = now
                self._send_alert_notification(alert)

    def _check_no_report(self, alert, now):
        """Check if the client hasn't reported within the threshold hours."""
        client = alert.client_id
        if not client.last_report_date:
            return True
        delta = now - client.last_report_date
        threshold_hours = alert.threshold_value or 48
        return delta > timedelta(hours=threshold_hours)

    def _check_version_below(self, alert):
        """Check if the client's Odoo version is below the minimum."""
        client = alert.client_id
        latest_report = self.env["lidoo.analytics.report"].search(
            [("client_id", "=", client.id)], order="report_date desc", limit=1
        )
        if not latest_report or not latest_report.odoo_version:
            return False
        min_version = alert.threshold_version or ""
        if not min_version:
            return False
        return latest_report.odoo_version < min_version

    def _check_db_size_exceeded(self, alert):
        """Check if the database size exceeds the threshold in GB."""
        client = alert.client_id
        latest_report = self.env["lidoo.analytics.report"].search(
            [("client_id", "=", client.id)], order="report_date desc", limit=1
        )
        if not latest_report:
            return False
        threshold_bytes = (alert.threshold_value or 0) * 1073741824  # GB to bytes
        return latest_report.database_size > threshold_bytes

    def _check_user_count_change(self, alert):
        """Check if active user count changed significantly between last two reports."""
        client = alert.client_id
        reports = self.env["lidoo.analytics.report"].search(
            [("client_id", "=", client.id)], order="report_date desc", limit=2
        )
        if len(reports) < 2:
            return False
        current = reports[0].active_user_count
        previous = reports[1].active_user_count
        if previous == 0:
            return current > 0
        change_pct = abs(current - previous) / previous * 100
        threshold_pct = alert.threshold_value or 20
        return change_pct >= threshold_pct

    def _send_alert_notification(self, alert):
        """Create a mail activity on the client record to notify the manager."""
        try:
            activity_type = self.env.ref("mail.mail_activity_data_warning")
        except Exception:
            activity_type = self.env["mail.activity.type"].search(
                [("res_model", "=", "lidoo.analytics.client")], limit=1
            ) or self.env["mail.activity.type"].search([], limit=1)

        alert.client_id.activity_schedule(
            act_type_xmlid="mail.mail_activity_data_warning",
            summary=f"Alert: {alert.name}",
            note=(
                f"Alert triggered for client <b>{alert.client_id.name}</b>.<br/>"
                f"Type: {dict(alert._fields['alert_type'].selection).get(alert.alert_type, alert.alert_type)}<br/>"
                f"Threshold: {alert.threshold_value}"
            ),
        )
        _logger.info(
            "Alert '%s' triggered for client '%s'.", alert.name, alert.client_id.name
        )

    @api.model
    def _cron_cleanup_old_reports(self):
        """Delete reports older than 90 days, keeping the latest per client."""
        cutoff = fields.Datetime.now() - timedelta(days=90)
        Report = self.env["lidoo.analytics.report"].sudo()

        old_reports = Report.search([("report_date", "<", cutoff)])
        if not old_reports:
            return

        # Group by client and protect the latest report for each
        clients = old_reports.mapped("client_id")
        to_delete = self.env["lidoo.analytics.report"]

        for client in clients:
            client_old_reports = old_reports.filtered(
                lambda r: r.client_id.id == client.id
            )
            # Keep the latest report for this client even if old
            latest = Report.search(
                [("client_id", "=", client.id)], order="report_date desc", limit=1
            )
            to_delete |= client_old_reports - latest

        if to_delete:
            count = len(to_delete)
            to_delete.unlink()
            _logger.info("Cleaned up %d old analytics reports.", count)
