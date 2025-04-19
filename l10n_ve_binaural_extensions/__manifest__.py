# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Venezuela - Binaural - Extensions",
    "website": "https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html",
    "icon": "/account/static/description/l10n.png",
    "author": "Odoo S.A., LIDALabs",
    "website": "https://lidalabs.com",
    "category": "Accounting/Localizations",
    "depends": [
        "base",
        "account",
        "l10n_ve_binaural",
        # "l10n_latam_base",
        "l10n_latam_invoice_document",
    ],
    "auto_install": [
        "account",
        "l10n_ve_binaural",
    ],
    "data": [
        "data/l10n_latam.document.type.csv",
        "data/res.bank.csv",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "license": "LGPL-3",
}
