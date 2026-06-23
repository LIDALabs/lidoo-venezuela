from odoo.tests.common import TransactionCase
from unittest.mock import patch, MagicMock

class TestPullClient(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Client = self.env['lidoo.analytics.client']
        self.client = self.Client.create({
            'name': 'Test Client',
            'sync_mode': 'pull',
            'target_url': 'http://test-client.com/analytics',
            'pull_api_key': 'test_key',
        })

    def test_pull_report_success(self):
        # Mock successful response
        mock_response = {
            'status': 'success',
            'data': {
                'database_uuid': 'new-uuid-123',
                'odoo_version': '17.0',
                'uptime_seconds': 3600,
                'database_size': 1024,
                'active_user_count': 5,
                'installed_modules': [{'name': 'base', 'version': '17.0'}],
            }
        }
        
        with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = mock_response
            
            # Execute
            res = self.client._pull_report()
            
            # Assert
            self.assertTrue(res)
            self.assertEqual(self.client.database_uuid, 'new-uuid-123')
            self.assertEqual(len(self.client.report_ids), 1)
            report = self.client.report_ids[0]
            self.assertEqual(report.uptime_seconds, 3600)
            
            # Verify headers
            mock_get.assert_called_with(
                'http://test-client.com/analytics',
                headers={'X-Lidoo-Api-Key': 'test_key'},
                timeout=30
            )

    def test_pull_report_failure(self):
         with patch('requests.get') as mock_get:
            mock_get.return_value.status_code = 500
            
            res = self.client._pull_report()
            
            self.assertFalse(res)
            self.assertEqual(len(self.client.report_ids), 0)
