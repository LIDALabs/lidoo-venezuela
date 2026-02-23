# -*- coding: utf-8 -*-
{
    'name': "Contizacion en Dolares",

    'summary': "Mostrar precios en USD en PDFs de cotizaciones",

    'description': """
    Permite mostrar precios en moneda extranjera (USD) en los PDFs de cotizaciones 
    de venta, sin modificar los valores originales en Bs del sistema. 
    Incluye un botón para activar/desactivar la conversión de moneda en los reportes.
    """,

    'author': "LIDALabs",
    'website': "https://lidalabs.com",
    'category': 'Sales',
    'version': '17.0.1.0.0',
    'images': ["static/description/l10n_ve.png"],
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base', 'l10n_ve_sale', 'sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/sale_order_view.xml',
    ],

}

