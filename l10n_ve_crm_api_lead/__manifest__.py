# -*- coding: utf-8 -*-
{
    'name': "API REST para Creación de Leads CRM",
    'summary': "Endpoint público para crear oportunidades en CRM vía API REST",
    'description': """
    Este módulo proporciona un endpoint API REST que permite la integración 
    de sistemas externos con el CRM de Odoo.
    
    Características principales:
    * Crear oportunidades/ leads mediante peticiones HTTP POST
    * Validación de datos obligatorios (nombre y teléfono)
    * Búsqueda automática de países por código
    * Creación automática de etiquetas CRM
    * Vinculación con socios existentes por email
    * Respuestas JSON estandarizadas
    """,

    'author': "LIDALabs",
    'website': "https://lidalabs.com",
    'category': 'API',
    'version': '17.0.1.2.0',
    "license": "LGPL-3",

    # any module necessary for this one to work correctly
    'depends': ['base', 'crm', 'lida_api_auth'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
    ],
    # Icon
    "images": ["static/description/l10n_ve.png"],
}

