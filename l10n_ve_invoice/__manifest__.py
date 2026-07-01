{
    "name": "Venezuela - Facturación",
    "summary": """
        Módulo de Facturación Venezuela
    """,
    "version": "17.0.0.0.13",
    "license": "LGPL-3",
    "author": "binaural-dev",
    "website": "https://binauraldev.com/",
    "category": "Accounting/Localizations/Account Chart",
    "depends": [
        "account",
        "l10n_ve_rate",
        "l10n_ve_base",
        "l10n_ve_accountant",
        "l10n_ve_contact",
        "l10n_ve_tax",
        "account_debit_note",
    ],
    "auto_install": [
        "account",
        "l10n_ve_base",
    ],
    "data": [
        "security/l10n_ve_invoice_groups.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/account_data.xml",
        "data/invoice_free_form_paperformat.xml",
        "data/invoice_preset_note_data.xml",
        "report/report_ir_actions_report.xml",
        "report/report_invoice_free_form.xml",
        "views/account_move.xml",
        "views/account_journal_views.xml",
        "views/menu.xml",
        "views/invoice_preset_note_views.xml",
        "views/res_config_settings.xml",
        "wizard/accounting_reports_views.xml",
        "views/account_debit_note_view.xml",
    ],
    "images": ["static/description/l10n_ve.png"],
    "application": True,
    "pre_init_hook": "pre_init_hook"
}
