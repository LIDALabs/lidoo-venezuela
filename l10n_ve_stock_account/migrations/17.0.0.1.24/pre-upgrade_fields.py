
import logging

from odoo.upgrade import util

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("Updating 'picking_ids'")
    util.convert_m2o_field_to_m2m(cr, 'account.move', 'picking_id', 'picking_ids', 'pickings_invoice_rel', 'account_move_id', 'stock_picking_id')
