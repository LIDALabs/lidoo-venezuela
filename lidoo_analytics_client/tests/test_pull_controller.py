from odoo.tests.common import HttpCase
from odoo.tools import mute_logger


class TestPullController(HttpCase):

    def test_pull_report_endpoint(self):
        # 1. Setup config
        ICP = self.env['ir.config_parameter']
        ICP.set_param('lidoo_analytics.enable_pull', 'True')
        ICP.set_param('lidoo_analytics.pull_api_key', 'test_key_123')

        # 2. Make Request
        # Note: HttpCase url_open makes a request to the server, which needs to be running.
        # However, standard Odoo tests are run with a test runner that handles this.
        # But if the server was started with typical run scripts, we are testing against a running server?
        # HttpCase usually starts a thread for the server in tests.

        response = self.url_open(
            '/api/lidoo/analytics/status',
            headers={'X-Lidoo-Api-Key': 'test_key_123'}
        )

        # 3. Assertions
        self.assertEqual(response.status_code, 200, "Should return 200 OK")
        t = response.json()
        self.assertEqual(t.get('status'), 'success', "Response status should be success")
        self.assertTrue('uptime_seconds' in t.get('data', {}), "Should contain uptime metrics")

    def test_pull_report_unauthorized(self):
        ICP = self.env['ir.config_parameter']
        ICP.set_param('lidoo_analytics.enable_pull', 'True')
        ICP.set_param('lidoo_analytics.pull_api_key', 'test_key_123')

        response = self.url_open(
            '/api/lidoo/analytics/status',
            headers={'X-Lidoo-Api-Key': 'wrong_key'}
        )
        self.assertEqual(response.status_code, 401, "Should return 401 Unauthorized")

    def test_pull_report_disabled(self):
        ICP = self.env['ir.config_parameter']
        ICP.set_param('lidoo_analytics.enable_pull', 'False')

        # Even with correct key, should be disabled
        response = self.url_open(
            '/api/lidoo/analytics/status',
            headers={'X-Lidoo-Api-Key': 'test_key_123'}
        )
        self.assertEqual(response.status_code, 403, "Should return 403 Forbidden when disabled")
