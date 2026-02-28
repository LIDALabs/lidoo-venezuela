import logging

_logger = logging.getLogger(__name__)

def migrate(cr, version):
    _logger.info('pre--> change bi_igtf to legacy_bi_igtf')
    from odoo.upgrade import util
    util.rename_field(cr, 'account.move', 'bi_igtf', 'legacy_bi_igtf')
    util.update_field_usage(cr, 'account.move', 'bi_igtf', 'legacy_bi_igtf')
