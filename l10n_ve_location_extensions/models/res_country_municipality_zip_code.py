import json
import logging
from odoo.tools import misc
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class ResCountryMunicipalityZipCode(models.Model):
    _name = 'res.country.municipality.zip.code'
    _description = 'Códigos Postales por Municipio'
    _order = 'name'

    name = fields.Char(string='Código Postal', required=True)
    municipality_id = fields.Many2one(
        'res.country.municipality', 
        string='Municipio', 
        required=True, 
        ondelete='cascade'
    )
    state_id = fields.Many2many(
        'res.country.state',
        related='municipality_id.state_id', 
        string='Estado'
    )

    @api.model
    def name_create(self, name):
        """Override name_create to support quick creation with municipality context."""
        municipality_id = self._context.get('default_municipality_id')
        if municipality_id:
            record = self.create({
                'name': name,
                'municipality_id': municipality_id,
            })
            return record.name_get()[0]
        return super(ResCountryMunicipalityZipCode, self).name_create(name)

    @api.model
    def load_zip_codes_from_json(self):
        _logger.info("Cargando códigos postales desde zip.json (via XML function)")
        try:
            json_file_path = misc.file_path('l10n_ve_location_extensions/data/zip.json')
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            state_model = self.env['res.country.state']
            municipality_model = self.env['res.country.municipality']
            
            state_cache = {}
            
            for item in data:
                estado_name = item.get('estado')
                municipio_name = item.get('municipio')
                codigos = item.get('codigos_postales', [])
                
                if not estado_name or not municipio_name or not codigos:
                    continue
                    
                if estado_name not in state_cache:
                    state = state_model.search([('name', '=', estado_name), ('country_id.code', '=', 'VE')], limit=1)
                    state_cache[estado_name] = state.id if state else False
                    
                state_id = state_cache.get(estado_name)
                if not state_id:
                    _logger.warning("Estado no encontrado: %s", estado_name)
                    continue
                    
                municipality = municipality_model.search([
                    ('name', '=', municipio_name),
                    ('state_id', '=', state_id)
                ], limit=1)
                
                if municipality:
                    for codigo in codigos:
                        existing = self.search([
                            ('name', '=', str(codigo)),
                            ('municipality_id', '=', municipality.id)
                        ], limit=1)
                        if not existing:
                            self.create({
                                'name': str(codigo),
                                'municipality_id': municipality.id
                            })
                else:
                    _logger.warning("Municipio no encontrado: %s en estado %s", municipio_name, estado_name)
        except Exception as e:
            _logger.error("Error al cargar códigos postales: %s", str(e))