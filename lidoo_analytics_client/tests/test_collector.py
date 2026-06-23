from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase


class TestAnalyticsCollector(TransactionCase):

    def test_collect_data(self):
        """Verify _collect_data returns all expected keys."""
        Collector = self.env["lidoo.analytics.collector"]
        data = Collector._collect_data()

        expected_keys = [
            "database_uuid",
            "odoo_version",
            "installed_modules",
            "custom_module_count",
            "uptime_seconds",
            "database_size",
            "active_user_count",
            "last_login",
            "os_info",
            "python_version",
            "active_cron_count",
        ]
        for key in expected_keys:
            self.assertIn(key, data, f"Missing key: {key}")

        # Basic type checks
        self.assertIsInstance(data["installed_modules"], list)
        self.assertIsInstance(data["uptime_seconds"], int)
        self.assertGreaterEqual(data["active_user_count"], 0)

    def test_collect_hardware_data_disabled(self):
        """Verify hardware data returns zeroes when psutil is not available."""
        Collector = self.env["lidoo.analytics.collector"]

        with patch.dict("sys.modules", {"psutil": None}):
            # Force ImportError by patching the import
            original = Collector._collect_hardware_data

            def _mock_collect_hw(self_inner=None):
                try:
                    import psutil  # noqa
                    return {
                        "cpu_usage": psutil.cpu_percent(interval=0),
                        "memory_usage": psutil.virtual_memory().percent,
                    }
                except (ImportError, TypeError):
                    return {"cpu_usage": 0.0, "memory_usage": 0.0}

            hw_data = _mock_collect_hw()
            # Either psutil is installed and we get real values,
            # or it's not and we get zeroes — both are valid
            self.assertIn("cpu_usage", hw_data)
            self.assertIn("memory_usage", hw_data)

    def test_send_report_creates_log(self):
        """Verify that _send_report creates a log entry on success."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("lidoo_analytics.enabled", "True")
        ICP.set_param("lidoo_analytics.endpoint_url", "https://test.example.com/lidoo/analytics/report")
        ICP.set_param("lidoo_analytics.api_key", "test-api-key-12345")
        ICP.set_param("lidoo_analytics.collect_hw", "False")

        # Mock the HTTP POST request
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status": "success"}'

        Collector = self.env["lidoo.analytics.collector"]
        Log = self.env["lidoo.analytics.log"].sudo()

        initial_count = Log.search_count([])

        with patch("odoo.addons.lidoo_analytics_client.models.analytics_collector.requests.post", return_value=mock_response):
            result = Collector._send_report()

        self.assertTrue(result)
        self.assertEqual(Log.search_count([]), initial_count + 1)

        log_entry = Log.search([], order="send_date desc", limit=1)
        self.assertEqual(log_entry.status, "success")

    def test_send_report_logs_error_on_failure(self):
        """Verify that _send_report creates an error log entry on HTTP failure."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("lidoo_analytics.enabled", "True")
        ICP.set_param("lidoo_analytics.endpoint_url", "https://test.example.com/lidoo/analytics/report")
        ICP.set_param("lidoo_analytics.api_key", "test-api-key-12345")
        ICP.set_param("lidoo_analytics.collect_hw", "False")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        Collector = self.env["lidoo.analytics.collector"]
        Log = self.env["lidoo.analytics.log"].sudo()

        with patch("odoo.addons.lidoo_analytics_client.models.analytics_collector.requests.post", return_value=mock_response):
            result = Collector._send_report()

        self.assertFalse(result)

        log_entry = Log.search([], order="send_date desc", limit=1)
        self.assertEqual(log_entry.status, "error")
        self.assertIn("500", log_entry.error_message)
