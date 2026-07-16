# -*- coding: utf-8 -*-
{
    'name': "LIDA Integration API",

    'summary': "Endpoints",

    'description': """""",

    'author': "LIDALabs",
    'website': "https://lidalabs.com",
    'category': 'API',
    'version': '0.2.0',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'lida_api_auth',
        'sale_management',
        'account',
        'l10n_ve_contact',
        'l10n_ve_sale',
        'l10n_ve_rate',
        'l10n_ve_invoice',
        'l10n_ve_tax',
        'l10n_ve_accountant',
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/webhook_event_views.xml',
        'views/res_config_settings_views.xml',
    ],
    # Icon
    "images": ["static/description/l10n_ve.png"],
}

