from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestAnalyticsAlert(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Client = self.env["lidoo.analytics.client"].sudo()
        self.Report = self.env["lidoo.analytics.report"].sudo()
        self.Alert = self.env["lidoo.analytics.alert"].sudo()

        self.test_client = self.Client.create({"name": "Alert Test Client"})

    def test_alert_no_report(self):
        """Alert triggers when client hasn't reported within threshold."""
        # Set the last report to 72 hours ago
        self.test_client.last_report_date = fields.Datetime.now() - timedelta(hours=72)

        alert = self.Alert.create(
            {
                "name": "No report in 48h",
                "client_id": self.test_client.id,
                "alert_type": "no_report",
                "threshold_value": 48,
            }
        )

        # Run the check
        self.Alert._cron_check_alerts()

        # The alert should have been triggered
        alert.invalidate_recordset()
        self.assertTrue(alert.last_triggered)

    def test_alert_no_report_not_triggered(self):
        """Alert does NOT trigger when client reported recently."""
        self.test_client.last_report_date = fields.Datetime.now() - timedelta(hours=1)

        alert = self.Alert.create(
            {
                "name": "No report in 48h",
                "client_id": self.test_client.id,
                "alert_type": "no_report",
                "threshold_value": 48,
            }
        )

        self.Alert._cron_check_alerts()

        alert.invalidate_recordset()
        self.assertFalse(alert.last_triggered)

    def test_alert_db_size_exceeded(self):
        """Alert triggers when database size exceeds threshold."""
        self.Report.create(
            {
                "client_id": self.test_client.id,
                "odoo_version": "17.0",
                "database_size": 5368709120,  # 5 GB
            }
        )

        alert = self.Alert.create(
            {
                "name": "DB > 4GB",
                "client_id": self.test_client.id,
                "alert_type": "db_size_exceeded",
                "threshold_value": 4,  # 4 GB
            }
        )

        self.Alert._cron_check_alerts()

        alert.invalidate_recordset()
        self.assertTrue(alert.last_triggered)

    def test_data_retention_cleanup(self):
        """Reports older than 90 days are deleted, except the latest per client."""
        now = fields.Datetime.now()

        # Create 3 reports: one current, two old
        self.Report.create(
            {
                "client_id": self.test_client.id,
                "report_date": now,
                "odoo_version": "17.0",
            }
        )
        old_report_1 = self.Report.create(
            {
                "client_id": self.test_client.id,
                "report_date": now - timedelta(days=100),
                "odoo_version": "17.0",
            }
        )
        old_report_2 = self.Report.create(
            {
                "client_id": self.test_client.id,
                "report_date": now - timedelta(days=120),
                "odoo_version": "17.0",
            }
        )

        initial_count = self.Report.search_count(
            [("client_id", "=", self.test_client.id)]
        )
        self.assertEqual(initial_count, 3)

        # Run cleanup
        self.Alert._cron_cleanup_old_reports()

        # Should have 1 remaining (the current one)
        remaining = self.Report.search([("client_id", "=", self.test_client.id)])
        self.assertEqual(len(remaining), 1)
        self.assertNotIn(old_report_1.id, remaining.ids)
        self.assertNotIn(old_report_2.id, remaining.ids)

    def test_client_status_computation(self):
        """Verify status is computed correctly based on last_report_date."""
        # No report → inactive
        self.test_client.invalidate_recordset()
        self.assertEqual(self.test_client.status, "inactive")

        # Recent report → active
        self.test_client.last_report_date = fields.Datetime.now()
        self.test_client.invalidate_recordset()
        self.assertEqual(self.test_client.status, "active")

        # 30 hours ago → warning
        self.test_client.last_report_date = fields.Datetime.now() - timedelta(hours=30)
        self.test_client.invalidate_recordset()
        self.assertEqual(self.test_client.status, "warning")

        # 72 hours ago → inactive
        self.test_client.last_report_date = fields.Datetime.now() - timedelta(hours=72)
        self.test_client.invalidate_recordset()
        self.assertEqual(self.test_client.status, "inactive")

    def test_api_key_auto_generated(self):
        """Verify API key is auto-generated on client creation."""
        client = self.Client.create({"name": "New Client"})
        self.assertTrue(client.api_key)
        self.assertEqual(len(client.api_key), 36)  # UUID format

    def test_api_key_regeneration(self):
        """Verify API key can be regenerated."""
        old_key = self.test_client.api_key
        self.test_client.action_regenerate_api_key()
        self.assertNotEqual(self.test_client.api_key, old_key)
