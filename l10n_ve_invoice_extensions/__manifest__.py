# -*- coding: utf-8 -*-
{
    "name": "Extensiones de Venezuela - Facturación",
    "summary": "Usa el modulo nativo l10n_latam_document_type para asignar números de documento.",
    "author": "LIDALabs",
    "website": "https://lidalabs.com",
    "category": "Accountant/Accountant",
    "version": "17.0.1.0.2",
    "license": "LGPL-3",
    "depends": ["account", "l10n_ve_invoice"],
    "auto_install": True,
    "application": False,
    "data": [
        "data/l10n_ve_invoice_groups.xml",
        "data/ir_sequence_data.xml",
        "views/account_journal_views.xml",
    ],
    "demo": [
    ],
}
