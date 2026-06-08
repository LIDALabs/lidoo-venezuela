from . import models
import logging

def _migrate_zip_codes(env):
    _logger = logging.getLogger(__name__)
    _logger.info("Starting zip code migration to zip_code_id...")

    cr = env.cr

    cr.execute("""
        SELECT id, zip, municipality
        FROM res_partner
        WHERE zip IS NOT NULL
        AND zip != ''
        AND (zip_code_id IS NULL OR zip_code_id = 0)
        AND municipality IS NOT NULL
    """)
    partners_to_migrate = cr.fetchall()

    if not partners_to_migrate:
        _logger.info("No partners need zip code migration.")
        return

    _logger.info(f"Found {len(partners_to_migrate)} partners to migrate.")
    migrated = 0
    errors = 0

    for partner_id, zip_value, municipality_id in partners_to_migrate:
        try:
            cr.execute("""
                SELECT id
                FROM res_country_municipality_zip_code
                WHERE name = %s
                AND municipality_id = %s
                LIMIT 1
            """, (zip_value, municipality_id))

            result = cr.fetchone()

            if result:
                zip_code_id = result[0]
            else:
                cr.execute("""
                    INSERT INTO res_country_municipality_zip_code
                    (name, municipality_id, create_uid, create_date, write_uid, write_date)
                    VALUES (%s, %s, %s, NOW(), %s, NOW())
                    RETURNING id
                """, (zip_value, municipality_id, env.uid, env.uid))
                zip_code_id = cr.fetchone()[0]

            cr.execute("""
                UPDATE res_partner
                SET zip_code_id = %s
                WHERE id = %s
            """, (zip_code_id, partner_id))

            migrated += 1

        except Exception as e:
            errors += 1
            _logger.error(f"Error migrating partner {partner_id}: {str(e)}")

    _logger.info(f"Zip code migration completed: {migrated} migrated, {errors} errors.")
