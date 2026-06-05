import json

from odoo.tests.common import HttpCase, tagged


@tagged("-at_install", "post_install")
class TestAnalyticsController(HttpCase):

    def setUp(self):
        super().setUp()
        self.Client = self.env["lidoo.analytics.client"].sudo()
        self.Report = self.env["lidoo.analytics.report"].sudo()

        # Create a test client record
        self.test_client = self.Client.create({"name": "Test Client"})
        self.api_key = self.test_client.api_key

    def test_receive_report_valid(self):
        """Send a valid report and assert it creates a report record."""
        payload = {
            "api_key": self.api_key,
            "database_uuid": "test-uuid-1234",
            "odoo_version": "17.0",
            "uptime_seconds": 3600,
            "database_size": 104857600,
            "active_user_count": 5,
            "installed_modules": [
                {"name": "base", "version": "17.0.1.0.0"},
            ],
            "os_info": "Linux 5.15.0 (x86_64)",
            "python_version": "3.10.12",
            "custom_module_count": 2,
            "cpu_usage": 25.0,
            "memory_usage": 60.0,
        }

        response = self.url_open(
            "/lidoo/analytics/report",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "success")

        # Verify a report was created
        reports = self.Report.search([("client_id", "=", self.test_client.id)])
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports.odoo_version, "17.0")
        self.assertEqual(reports.active_user_count, 5)

        # Verify the client's database_uuid was updated
        self.test_client.invalidate_recordset()
        self.assertEqual(self.test_client.database_uuid, "test-uuid-1234")

    def test_receive_report_invalid_key(self):
        """Send a report with an invalid API key and assert 403."""
        payload = {
            "api_key": "invalid-key-999",
            "database_uuid": "test-uuid-1234",
            "odoo_version": "17.0",
        }

        response = self.url_open(
            "/lidoo/analytics/report",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 403)
        result = response.json()
        self.assertEqual(result["status"], "error")

    def test_receive_report_missing_key(self):
        """Send a report without an API key and assert 400."""
        payload = {
            "database_uuid": "test-uuid-1234",
            "odoo_version": "17.0",
        }

        response = self.url_open(
            "/lidoo/analytics/report",
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 400)

    def test_receive_report_empty_body(self):
        """Send an empty body and assert 400."""
        response = self.url_open(
            "/lidoo/analytics/report",
            data=b"",
            headers={"Content-Type": "application/json"},
        )

        self.assertEqual(response.status_code, 400)
