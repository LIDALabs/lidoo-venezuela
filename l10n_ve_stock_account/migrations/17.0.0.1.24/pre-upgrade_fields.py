
import logging

from odoo.tools.sql import column_exists

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    # Ensure columns from res_company exist even if previous install was partial
    _logger.info("Ensuring l10n_ve_stock_account columns exist on res_company")
    cr.execute("""
        ALTER TABLE res_company
        ADD COLUMN IF NOT EXISTS optional_internal_movement_guidance BOOLEAN DEFAULT FALSE
    """)
    cr.execute("""
        ALTER TABLE res_company
        ADD COLUMN IF NOT EXISTS invoice_cron_type VARCHAR DEFAULT 'last_business_day'
    """)
    cr.execute("""
        ALTER TABLE res_company
        ADD COLUMN IF NOT EXISTS invoice_cron_time DOUBLE PRECISION DEFAULT 18.0
    """)
    cr.execute("""
        ALTER TABLE res_company
        ADD COLUMN IF NOT EXISTS hide_price_on_dispatch_guide BOOLEAN DEFAULT FALSE
    """)

    _logger.info("Updating 'picking_ids'")
    if not column_exists(cr, 'account_move', 'picking_id'):
        return

    # Create the M2M relation table if it doesn't exist
    cr.execute("""
        CREATE TABLE IF NOT EXISTS pickings_invoice_rel (
            account_move_id INTEGER NOT NULL
                REFERENCES account_move(id) ON DELETE CASCADE,
            stock_picking_id INTEGER NOT NULL
                REFERENCES stock_picking(id) ON DELETE CASCADE,
            PRIMARY KEY (account_move_id, stock_picking_id)
        )
    """)

    # Migrate data from M2O (picking_id) to M2M (picking_ids)
    cr.execute("""
        INSERT INTO pickings_invoice_rel (account_move_id, stock_picking_id)
        SELECT id, picking_id
        FROM account_move
        WHERE picking_id IS NOT NULL
        ON CONFLICT DO NOTHING
    """)

    # Drop the old M2O column
    cr.execute("ALTER TABLE account_move DROP COLUMN IF EXISTS picking_id")
    _logger.info("Migrated 'picking_id' (M2O) to 'picking_ids' (M2M)")
