# -*- coding: utf-8 -*-
{
    "name": "Venezuela - IGTF extensiones",
    "summary": "",
    "author": "LIDALabs",
    "website": "https://lidalabs.com",
    "category": "Accountant/Accountant",
    "version": "17.0.1.1.1",
    "license": "LGPL-3",
    'depends': [
        'account',
        'l10n_ve_igtf',
        'l10n_ve_invoice',
        'l10n_ve_invoice_extensions'
    ],
    'auto_install': True,
    'application': False,
    'data': [
    ],
    "post_init_hook": "setup_accounts",
}
