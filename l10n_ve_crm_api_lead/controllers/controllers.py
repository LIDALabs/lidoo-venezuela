# -*- coding: utf-8 -*-
import logging
import json

from odoo import http
from odoo.http import request, route
from odoo.addons.lida_api_auth.decorators import require_api_key

_logger = logging.getLogger(__name__)

class LeadController(http.Controller):
    
    @require_api_key()
    @route('/api/lead/create', type='http', auth='public', methods=['POST'], csrf=False)
    def create_lead(self, **kw):
        data = {}
        try: 
            raw_data = request.httprequest.data
            if not raw_data:
                return self._response({'status': 'error', 'message': 'empty body'}, 400)
            try:
                data = json.loads(raw_data)
                ...
            except ValueError:
                return self._response({'status': 'error', 'message': 'JSON invalid'}, 400)
            
            # Validaciones
            if not data.get('name') or not data.get('phone'):
                return self._response({'status': 'error', 'message': 'Missing Name or Phone'}, 400)
            
            country_id = False
            if data.get('country_code'):
                Country = request.env['res.country']
                country = Country.sudo().search([('code', '=', data.get('country_code'))], limit=1)
                country_id = country.id if country else False

            tag_ids = []
            if data.get('tag_names'): 
                for tag in data.get('tag_names'): 
                    Tag = request.env['crm.tag']
                    crm_tag = Tag.sudo().search([('name', '=', tag)], limit=1)
                    if not crm_tag: 
                        crm_tag = Tag.sudo().create({'name': tag})
                    tag_ids.append(crm_tag.id)
            
            partner_id = False
            Partner = request.env['res.partner']
            existing_partner = Partner.sudo().search([
                ('email', '=', data.get('email')),
            ], limit=1)
            if existing_partner: 
                partner_id = existing_partner.id
            
            # Preparando la Data
            vals = { 
                'name': data.get('name'),
                'contact_name': data.get('contact_name', ''),
                'partner_name': data.get('partner_name', ''),
                'partner_id': partner_id,
                'email_from': data.get('email', ''),
                'phone': data.get('phone'),
                'mobile': data.get('mobile', ''),
                'function': data.get('function', ''),
                'street': data.get('street', ''),
                'city': data.get('city', ''),
                'zip': data.get('zip', ''),
                'country_id': country_id,
                'expected_revenue': data.get('expected_revenue', 0.0),
                'priority': data.get('priority', 0),
                'tag_ids': [(6, 0, tag_ids)],
                'description': data.get('notes', ''),
                'type': 'opportunity',
                'user_id': request.env.ref('base.user_admin').id
            }

            try:
                ...
                Lead = request.env['crm.lead']
                new_lead = Lead.sudo().create(vals)

                return self._response({
                    'status': 'success',
                    'lead_id': new_lead.id,
                    'message': f'Oportunidad {new_lead.name} creada exitosamente'
                })


            except Exception as e:
                return self._response({'status': 'error', 'message': str(e)}, 500)
            
            ...
        except Exception as e:
            _logger.exception("Error en la API create lead")
            return self._response({'status': 'error', 'message': str(e)}, 500)
            ...
        ...


    def _response(self, data, status=200):
        # * Helper para dar una respuesta JSON para el type="http"
        return request.make_response(
            json.dumps(data),
            headers=[('Content-Type', 'application/json')],
            status=status
        )
        ...