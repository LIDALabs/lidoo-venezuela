# -*- coding: utf-8 -*-
{
    'name': "API Authentication",

    'summary': "API Key authentication for external integrations",

    'description': """
    Módulo para gestionar API Keys y autenticación de endpoints externos.
    Permite generar keys, validar headers y proteger rutas API.
    """,

    'author': "LIDALabs",
    'website': "https://lidalabs.com",
    'category': 'API',
    'version': '17.0.1.0.0',
    'depends': ['base', 'web'],
    'license': 'LGPL-3',
    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/res_config_settings_view.xml'
    ],
    # icon
    "images": ["static/description/l10n_ve.png"]
}

