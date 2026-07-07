from odoo import tools


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cr.fetchone() is not None


def migrate(cr, version):
    # During upgrades the invoice_preset_note table may not exist yet (e.g. the
    # previous update was interrupted), but account.move's stored computed field
    # preset_note_text reads the company-dependent preset_note_id, which joins
    # ir_property with invoice_preset_note. Without the table the recompute
    # crashes the registry initialization.
    if not tools.table_exists(cr, "invoice_preset_note"):
        cr.execute(
            """
            CREATE TABLE invoice_preset_note (
                id SERIAL NOT NULL,
                name JSONB NOT NULL,
                text JSONB NOT NULL,
                active BOOLEAN DEFAULT TRUE,
                create_uid INTEGER,
                create_date TIMESTAMP WITHOUT TIME ZONE,
                write_uid INTEGER,
                write_date TIMESTAMP WITHOUT TIME ZONE,
                CONSTRAINT invoice_preset_note_pkey PRIMARY KEY (id)
            )
            """
        )

    # Remove stale ir.property rows referencing the preset note model. They are
    # useless if the target record/table is missing and would otherwise break the
    # company-dependent field read during model initialization.
    cr.execute(
        """
        DELETE FROM ir_property
        WHERE value_reference LIKE 'invoice.preset.note,%'
        """
    )

    # Ensure the res.company column added by this module exists. In some
    # interrupted upgrades the ORM may not have created it, which makes every
    # res_company read crash with UndefinedColumn.
    if not _column_exists(cr, "res_company", "auto_select_debit_note_journal"):
        cr.execute(
            """
            ALTER TABLE res_company
            ADD COLUMN auto_select_debit_note_journal BOOLEAN DEFAULT FALSE
            """
        )

    # Odoo.sh builds occasionally fail to recreate transient model tables when
    # restoring from a production backup. The autovacuum cron then crashes
    # because it tries to query non-existent tables. Create minimal tables so
    # the ORM can add the remaining columns during init_models.
    transient_tables = [
        "account_initial_balance_import",
        "account_initial_balance_import_line",
        "lidoo_analytics_ticket_wizard",
        "inventory_calculator_process",
    ]
    for table in transient_tables:
        if not tools.table_exists(cr, table):
            cr.execute(
                f"""
                CREATE TABLE {table} (
                    id SERIAL NOT NULL,
                    create_uid INTEGER,
                    create_date TIMESTAMP WITHOUT TIME ZONE,
                    write_uid INTEGER,
                    write_date TIMESTAMP WITHOUT TIME ZONE,
                    CONSTRAINT {table}_pkey PRIMARY KEY (id)
                )
                """
            )
