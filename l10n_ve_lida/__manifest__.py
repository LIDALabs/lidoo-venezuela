# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Venezuela - Plan de cuentas",
    "category": "Accounting/Localizations/Account Charts",
    "website": "https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html",
    "icon": "/account/static/description/l10n.png",
    "countries": ["ve"],
    "license": "LGPL-3",
    "version": "17.0.1.2.0",
    "description": """
        Plantilla de plan de cuentas de servicio donde se agregan las
        cuentas contables y diarios para tipo de empresa servicio
""",
    "depends": [
        "base",
        "account",
        "account_accountant",
        "account_base_import",
        "stock",
        "sale",
        "contacts",
        "l10n_latam_invoice_document",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/l10n_latam.document.type.csv",
        "data/res.bank.csv",
        "wizard/account_chart_replace_wizard_views.xml",
        "views/account_chart_replace_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
}
