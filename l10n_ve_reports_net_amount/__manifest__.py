# -*- coding: utf-8 -*-
{
    'name': "l10n_ve_reports_net_amount",

    'summary': "Permite generar reportes sobre las cantidade netas de producto comprado",

    'description': """""",
    "license": "LGPL-3",
    'author': "LIDALabs",
    'website': "https://lidalabs.com",
    'category': 'Stocks',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', "product", "stock", 'purchase'],

    # image icon
    "images": ["static/description/l10n_ve.png"],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/net_amount_wizard.xml',
        'report/report_net_amount_templates.xml',
        'report/report_net_amount.xml',
        'views/net_amount_result.xml',
    ],
    "application": True,
}

