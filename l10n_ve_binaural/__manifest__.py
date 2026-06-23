# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Venezuela - Plan de cuentas',
    'category': 'Accounting/Localizations/Account Charts',
    'website': 'https://www.odoo.com/documentation/17.0/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ve'],
    'license': 'LGPL-3',
    "version": "17.0.0.0.4",
    'description': """
        Plantilla de plan de cuentas de servicio donde se agregan las
        cuentas contables y diarios para tipo de empresa servicio
""",
    'depends': ['base', 'account', "account_accountant", "stock", "sale", "contacts", 'l10n_ve_binaural_pre'],
    "demo": [
        "demo/demo_company.xml",
    ],
}
