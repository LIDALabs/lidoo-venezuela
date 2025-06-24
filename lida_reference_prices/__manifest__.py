# -*- coding: utf-8 -*-
{
    'name': "Precios referenciales",
    'summary': "Permite crear listas de precios referenciales",
    'description': """""",

    "author": "LIDALabs",
    "website": "https://lidalabs.com",
    "category": "Sales",
    "version": "17.0.1.0.0",
    "depends": [
        "product",
        "sale",
        "l10n_ve_sale",
    ],
    "data": [
        # 'security/ir.model.access.csv',
        'data/product_pricelist_data.xml',
        'data/ir_cron_data.xml',
        'views/product_pricelist_views.xml',
        'views/res_config_settings_views.xml',
    ],
    "license": "LGPL-3",
    'demo': [
        # 'demo/demo.xml',
    ],
}
