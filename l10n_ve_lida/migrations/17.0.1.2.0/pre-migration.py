import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    _logger.info("Ensuring l10n_ve_lida default account columns exist on res_company")
    cr.execute("""
        ALTER TABLE res_company
        ADD COLUMN IF NOT EXISTS account_receivable_id INTEGER
    """)
    cr.execute("""
        ALTER TABLE res_company
        ADD COLUMN IF NOT EXISTS account_payable_id INTEGER
    """)
