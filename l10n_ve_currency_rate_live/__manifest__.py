{
    "name": "Venezuela - Sincronización de Tasa de Cambio",
    "summary": "Fijar automáticamente el tipo de cambio oficial de Venezuela (tipo BCV).",
    "license": "LGPL-3",
    "author": "binaural-dev",
    "website": "https://binauraldev.com/",
    "category": "Technical",
    "version": "17.0.1.1.1",
    "depends": ["l10n_ve_rate", "currency_rate_live", "lida_reference_prices"],
    "images": ["static/description/l10n_ve.png"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/bcv_rate_wizard_view.xml",
        "views/res_config_settings.xml",
        "views/res_currency_views.xml",
    ],
    "post_init_hook": "_post_init_hook",
}
