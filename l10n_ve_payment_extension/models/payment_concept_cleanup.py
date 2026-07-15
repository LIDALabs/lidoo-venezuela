from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PaymentConceptCleanup(models.Model):
    _name = 'payment.concept.cleanup'
    _description = 'Payment Concept Cleanup'

    name = fields.Char(string='Name', default='Payment Concept Cleanup')
    active = fields.Boolean(string='Active', default=True)

    @api.model
    def _cleanup_old_payment_concepts(self):
        """
        Elimina conceptos de pago viejos (sin códigos en el nombre) y duplicados.
        Se ejecuta periódicamente mediante cron job.
        """
        _logger.info("Iniciando limpieza de conceptos de pago viejos y duplicados")
        
        # Eliminar conceptos viejos (sin códigos en el nombre)
        old_names = [
            'Honorarios Profesionales Pagados a',
            'Gastos de Transporte (Fletes) Pagados a',
            '(Contratista) Ejecución de obras y prestación de servicios en Venezuela pagadas a:',
            'Arrendamiento de bienes muebles pagado a:',
            'Arrendamiento o cesión de uso de bienes inmuebles, pagados al arrendador por personas jurídicas, comunidades o los administradores:',
            'Publicidad, propaganda y venta de espacios pagadas a',
            'Comisiones pagadas a',
        ]
        
        deleted_count = 0
        
        for name in old_names:
            # Buscar conceptos con este nombre
            concepts = self.env['payment.concept'].search([('name', '=', name)])
            
            if concepts:
                # Eliminar líneas asociadas
                for concept in concepts:
                    self.env.cr.execute(
                        """
                        DELETE FROM payment_concept_line 
                        WHERE payment_concept_id = %s
                        """,
                        (concept.id,)
                    )
                
                # Eliminar conceptos
                concepts.unlink()
                deleted_count += len(concepts)
                _logger.info(f"Eliminados {len(concepts)} conceptos con nombre: {name}")
        
        # Eliminar duplicados (conceptos con el mismo nombre, mantener solo el más nuevo)
        self.env.cr.execute(
            """
            DELETE FROM payment_concept_line 
            WHERE payment_concept_id IN (
                SELECT id FROM payment_concept 
                WHERE id NOT IN (
                    SELECT MAX(id) FROM payment_concept GROUP BY name
                )
            )
            """
        )
        
        self.env.cr.execute(
            """
            DELETE FROM payment_concept 
            WHERE id NOT IN (
                SELECT MAX(id) FROM payment_concept GROUP BY name
            )
            """
        )
        
        # Contar conceptos restantes
        remaining_count = self.env['payment.concept'].search_count([])
        
        _logger.info(f"Limpieza completada. Eliminados {deleted_count} conceptos viejos. "
                    f"Quedan {remaining_count} conceptos en la base de datos.")
        
        return {
            'deleted_old': deleted_count,
            'remaining': remaining_count
        }
