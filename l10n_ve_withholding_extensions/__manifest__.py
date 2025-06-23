# -*- coding: utf-8 -*-
{
    "name": "Extensiones de Venezuela - Retenciones",
    "summary": """Extiende el Módulo de Retenciones Venezuela""",
    "author": "LIDALabs",
    "website": "https://lidalabs.com",
    "category": "Accountant/Accountant",
    "version": "17.0.1.2.0",
    "license": "LGPL-3",
    "depends": ["account", "l10n_ve_payment_extension"],
    "auto_install": True,
    "application": False,
    "data": [
        "views/account_move_views.xml",
        "views/retention_line_report_views.xml",
    ],
    "demo": [
    ],
}
