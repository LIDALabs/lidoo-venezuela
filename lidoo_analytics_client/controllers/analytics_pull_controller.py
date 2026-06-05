import json
import logging

from odoo import http
from odoo.http import request, route

_logger = logging.getLogger(__name__)


class LidooAnalyticsPullController(http.Controller):

    @route('/api/lidoo/analytics/status', type='http', auth='public', methods=['GET'], csrf=False)
    def get_analytics_status(self, **kw):
        """Expose analytics data via Pull API."""
        ICP = request.env['ir.config_parameter'].sudo()

        # 1. Check if Pull Mode is enabled
        enable_pull = ICP.get_param('lidoo_analytics.enable_pull', default='False')
        if enable_pull.lower() not in ('true', '1', 'yes'):
            return self._response({'status': 'error', 'message': 'Unauthorized'}, 401)

        # 2. Validate API Key
        pull_api_key = ICP.get_param('lidoo_analytics.pull_api_key', default='')
        request_key = request.httprequest.headers.get('X-Lidoo-Api-Key')

        if not pull_api_key or request_key != pull_api_key:
            return self._response({'status': 'error', 'message': 'Unauthorized'}, 401)

        # 3. Collect Data
        try:
            Collector = request.env['lidoo.analytics.collector'].sudo()
            data = Collector._collect_data()

            # Add hardware data if configured (Pull mode could force this, or respect existing setting)
            # Respect existing setting for now to match push behavior logic or just include it?
            # Plan didn't specify, but let's be consistent with push.
            collect_hw = ICP.get_param('lidoo_analytics.collect_hw', default='False')
            if collect_hw.lower() not in ('false', '0', ''):
                hw_data = Collector._collect_hardware_data()
                data.update(hw_data)

            return self._response({
                'status': 'success',
                'data': data
            })

        except Exception as e:
            _logger.exception("Error collecting pull analytics.")
            return self._response({'status': 'error', 'message': str(e)}, 500)

    def _response(self, data, status=200):
        return request.make_response(
            json.dumps(data, default=str),
            headers=[('Content-Type', 'application/json')],
            status=status
        )
