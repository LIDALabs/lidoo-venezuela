{
    "name": "Venezuela - Compras",
    "version": "17.0.0.0.0",
    "license": "LGPL-3",
    "summary": "Módulo para gestionar compras en Venezuela",
    "description": """
        Este módulo personaliza el proceso de gestión de compras para cumplir con las regulaciones venezolanas.
    """,
    "author": "binaural-dev",
    "website": "https://binauraldev.com/",
    "category": "Purchase",
    "depends": ["account", "stock", "product", "purchase"],
    'auto_install': True,
    "data": [
        "security/ir.model.access.csv",
        "views/product_view.xml",
    ],
    "application": True,
    "images": ["static/description/icon.png"],
}

