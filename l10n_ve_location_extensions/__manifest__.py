{
    "name": "Venezuela - DPT extensiones",
    "summary": """
       Módulo para extender Venezuela - DPT
    """,
    "license": "LGPL-3",
    "author": "LIDALabs",
    "website": "https://lidalabs.com",
    "category": "Accounting/Accounting",
    "version": "17.0.1.0.4",
    "depends": ["base", "l10n_ve_location"],
    "data": [
        "security/ir.model.access.csv",
        "data/load_zip_data.xml",
        "views/res_partner_views.xml",
    ],
    "images": ["static/description/l10n_ve.png"],
    "auto_install": False,
    "application": False,
}
