{
    "name": "Venezuela - Sincronización de Tasa de Cambio",
    "summary": "Fijar automáticamente el tipo de cambio oficial de Venezuela (tipo BCV).",
    "license": "LGPL-3",
    "author": "binaural-dev",
    "website": "https://binauraldev.com/",
    "category": "Technical",
    "version": "17.0.1.1.3",
    "installable": True,
    "depends": ["l10n_ve_rate", "currency_rate_live", "lida_reference_prices", "account_accountant"],
    "images": ["static/description/l10n_ve.png"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings.xml",
        "views/bcv_rate_log_views.xml",
        "wizard/bcv_rate_wizard_view.xml"
    ],
    "post_init_hook": "setup_currency_update",
}
