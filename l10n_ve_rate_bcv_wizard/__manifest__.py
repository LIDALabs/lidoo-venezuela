# -*- coding: utf-8 -*-
{
    'name': "Asistente de Precios - Tasa BCV",
    'summary': "Asistente para consultar la tasa del BCV y actualizar precios de productos",
    'description': """
    Es un wizard (asistente) que permite obtener el tipo de cambio oficial del Banco Central de Venezuela (BCV) y aplicar automáticamente esos valores para actualizar los precios de los productos en el sistema.
    """,

    'author': "LIDALabs",
    'website': "https://lidalabs.com",
    'category': 'Accounting',
    'version': '17.0.1.1.0',
    'license': 'LGPL-3',
    'depends': ['l10n_ve_currency_rate_live', 'lida_reference_prices'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/bcv_rate_wizard_view.xml',
        'views/res_currency_views.xml',
    ],
    "images": ["static/description/l10n_ve.png"],
}
