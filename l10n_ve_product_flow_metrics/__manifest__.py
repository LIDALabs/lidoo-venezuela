# -*- coding: utf-8 -*-
{
    'name': "Venezuela - Métricas de flujo de productos",

    'summary': "Métricas del flujo de compras y ventas de un producto",

    'description': """
        Muestra las metricas (Vendido, Ventas devueltas, Comprado, Compras devuelta) de un producto seleccionado, 
        aparte de mostrar esas metricas, tambien muestra el balance neto de las ventas y las compras. Y por ultimo 
        genera un reporte impreso de dichas metricas
    """,
    "license": "LGPL-3",
    'author': "LIDALabs",
    'website': "https://lidalabs.com",
    'category': 'Inventario',
    'version': '17.0.2.10.0',

    # any module necessary for this one to work correctly
    'depends': ['base', "product", "stock", 'purchase'],

    # image icon
    "images": ["static/description/l10n_ve.png"],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/flow_metrics_wizard.xml',
        'report/report_flow_metrics_templates.xml',
        'report/report_flow_metrics.xml',
        'views/flow_metrics.xml',
    ],
    "application": True,
}

