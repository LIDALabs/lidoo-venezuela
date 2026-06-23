# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Migrate zip codes from zip (Char) to zip_code_id (Many2one).
    This runs automatically when the module is updated.
    """
    _logger.info("Starting zip code migration to zip_code_id...")
    
    # Find all partners with zip but without zip_code_id
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
            # Search for existing zip_code_id
            cr.execute("""
                SELECT id
                FROM res_country_municipality_zip_code
                WHERE name = %s
                AND municipality_id = %s
                LIMIT 1
            """, (zip_value, municipality_id))
            
            result = cr.fetchone()
            
            if result:
                # Use existing zip_code_id
                zip_code_id = result[0]
            else:
                # Create new zip_code_id
                cr.execute("""
                    INSERT INTO res_country_municipality_zip_code
                    (name, municipality_id, create_uid, create_date, write_uid, write_date)
                    VALUES (%s, %s, %s, NOW(), %s, NOW())
                    RETURNING id
                """, (zip_value, municipality_id, 1, 1))
                zip_code_id = cr.fetchone()[0]
            
            # Update partner with zip_code_id
            cr.execute("""
                UPDATE res_partner
                SET zip_code_id = %s,
                    write_date = NOW()
                WHERE id = %s
            """, (zip_code_id, partner_id))
            
            migrated += 1
            
        except Exception as e:
            errors += 1
            _logger.error(f"Error migrating partner {partner_id}: {str(e)}")
    
    _logger.info(f"Zip code migration completed: {migrated} migrated, {errors} errors.")
