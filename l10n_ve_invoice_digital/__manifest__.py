{
    "name": "Venezuela - Facturación Digital",
    "license": "LGPL-3",
    "author": "binaural-dev",
    "website": "https://binauraldev.com/",
    "category": "Accounting/Accounting",
    "version": "17.0.0.0.3",
    "depends": [
        "account",
        "l10n_ve_igtf",
        "account_debit_note",
        "l10n_ve_invoice",
        "l10n_ve_iot_mf",
        "l10n_ve_stock_account",
        "l10n_ve_payment_extension",
        "stock",
        "lida_NOT_SUPPORTED"
    ],
    
    "images": ["static/description/icon.png"],
    "application": False,
    "installable": True,
    "auto_install": False,
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings.xml",
        "views/account_move_view.xml",
        "views/account_retention_iva.xml",
        "views/account_retention_islr.xml",
        "views/stock_picking.xml",
        "wizard/account_retention_alert_views.xml",
        "views/account_journal.xml",
    ],
}
