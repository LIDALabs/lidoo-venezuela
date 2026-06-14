{
    "name": "LIDA Analytics Client",
    "summary": """
        Collects instance analytics and sends them to the partner instance.
    """,
    "description": """
        Client-side module for partner analytics.
        Collects database UUID, Odoo version, uptime, active users,
        database size, installed modules, and optional hardware metrics,
        then sends them periodically to a configured partner endpoint.
    """,
    "license": "LGPL-3",
    "author": "LIDALabs",
    "website": "https://lidalabs.com",
    "category": "Technical",
    "version": "17.0.1.1.0",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/analytics_log_views.xml",
        "data/ir_cron.xml",
    ],
    "auto_install": False,
    "assets": {
        "web.assets_backend": [
            "lidoo_analytics_client/static/src/ticket/ticket_systray.js",
            "lidoo_analytics_client/static/src/ticket/ticket_systray.xml",
        ],
    },
}
