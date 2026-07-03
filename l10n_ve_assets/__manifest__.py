{
    "name": "Assets Manager",
    "summary": "Upload and install system assets like fonts from Odoo",
    "version": "17.0.1.0.0",
    "category": "Technical",
    "author": "LIDA Labs",
    "website": "https://github.com/LIDALabs/lidoo-venezuela",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_font_views.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
