# -*- coding: utf-8 -*-
{
    "name": "Extensiones de Venezuela - Facturación",
    "summary": "Usa el modulo nativo l10n_latam_document_type para asignar números de documento.",
    "author": "LIDALabs",
    "website": "https://lidalabs.com",
    "category": "Accountant/Accountant",
    "version": "17.0.1.2.1",
    "license": "LGPL-3",
    "depends": ["account", "l10n_ve_invoice", "l10n_latam_invoice_document"],
    "auto_install": True,
    "application": False,
    "data": [
        "security/ir.model.access.csv",
        "data/l10n_ve_invoice_groups.xml",
        "data/ir_sequence_data.xml",
        # "data/report_paperformat_data.xml",
        "views/account_journal_views.xml",
        "report/invoice_payments_template.xml",
        "report/invoice_payments_report.xml",
        "wizard/invoice_payments_reports_wizard.xml",
        "views/menu.xml",
        "views/res_config_settings.xml",
        "views/account_move_views.xml",
    ],
    "demo": [
    ],
}
