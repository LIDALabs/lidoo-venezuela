import logging

_logger = logging.getLogger(__name__)
from odoo.tools.sql import column_exists

def migrate(cr, version):
    _logger.info('pre--> create column igtf_base_amount')
    if not column_exists(cr, 'account_move', 'igtf_base_amount'):
        from odoo.upgrade import util
        util.copy_column(cr, 'account_move', 'bi_igtf', new_name="igtf_base_amount")