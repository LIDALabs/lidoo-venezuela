from odoo import tools


def migrate(env, version):
    cr = env.cr

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
