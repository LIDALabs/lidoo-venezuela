# -*- coding: utf-8 -*-
{
    'name': "l10n_ve_rate_bcv_wizard",
    'summary': "Wizard to consult BCV rate and update product prices.",
    'description': """""",
    'author': "LIDALabs",
    'website': "https://lidalabs.com",
    'category': 'Accounting',
    'version': '1.1.0',
    'license': 'LGPL-3',
    'depends': ['l10n_ve_currency_rate_live', 'lida_reference_prices'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/bcv_rate_wizard_view.xml',
        'views/res_currency_views.xml',
    ],
    'installable': True,
    "images": ["static/description/l10n_ve.png"],
}
