
import logging 
from odoo.upgrade import util

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    _logger.info('Rename: l10n_ve_api_auth --> lida_api_auth')
    util.rename_module(cr, 'l10n_ve_api_auth', 'lida_api_auth')
    ...