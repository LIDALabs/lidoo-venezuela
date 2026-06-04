{
    "name": "Venezuela - DPT extensiones",
    "summary": """
       Módulo para extender Venezuela - DPT
    """,
    "license": "LGPL-3",
    "author": "LIDALabs",
    "website": "https://lidalabs.com",
    "category": "Accounting/Accounting",
    "version": "17.0.1.0.5",
    "depends": ["base", "l10n_ve_location"],
    "data": [
        "security/ir.model.access.csv",
        "data/load_zip_data.xml",
        "views/res_partner_views.xml",
    ],
    "post_init_hook": "_migrate_zip_codes",
    "images": ["static/description/l10n_ve.png"],
    "auto_install": False,
    "application": False,
}
