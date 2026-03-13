from functools import wraps
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

def _response_error(message, status=401):
    """ Helper to return JSON error response """
    return request.make_response(
        json.dumps({'status': 'error', 'message': message }),
        headers=[('Content-Type', 'application/json')],
        status=status
    )
    ...

def require_api_key():
    """
    Decorator to require valid API key for route
    
    Usage:
        @require_api_key()
        @route('/api/endpoint', type='http', auth='none', methods=['POST'])
        def my_endpoint(self, **kw):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            ICP = request.env['ir.config_parameter'].sudo()

            # 1. Check if Pull Mode is enabled
            enable_pull = ICP.get_param('api_auth.enable_pull', default='False')
            if enable_pull.lower() not in ('true', '1', 'yes'):
                _logger.warning(f"API access denied: Unauthorized for {func.__name__}")
                return _response_error('API key required. Provide X-Lidoo-Api-Key header or api_key param')
            
            # 2. Validate API key
            pull_api_key = ICP.get_param('api_auth.pull_api_key', default='')
            resquest_key = (
                request.httprequest.headers.get('X-Lidoo-Api-Key') or 
                request.params.get('api_key')
            )

            if not pull_api_key or resquest_key != pull_api_key:
                _logger.warning(f"API access denied: Unauthorized for {func.__name__}")
                return _response_error('No match Api Keys.')
            
            return func(self, *args, **kwargs)
        return wrapper
    return decorator
