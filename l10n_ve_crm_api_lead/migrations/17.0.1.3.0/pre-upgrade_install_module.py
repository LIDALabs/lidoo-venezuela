import logging

from odoo.upgrade import util

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    _logger.info("Verify if install CRM; if not installed, will do forced install")
    if not util.module_installed(cr, 'crm'):
        util.force_install_module(cr, 'crm', if_installed=None, reason="Es necesario este modulo para visualizar los leads generados")
    _logger.info("Verify if install lida_api_auth; if not installed, will do forced install")
    if not util.module_installed(cr, 'lida_api_auth'):
        util.force_install_module(cr, 'lida_api_auth', if_installed=None, reason="Es necesario para proteger los endpoints")
    ...
