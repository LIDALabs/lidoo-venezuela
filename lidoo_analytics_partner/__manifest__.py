{
    "name": "LIDA Analytics Partner",
    "summary": """
        Receives and displays analytics from client instances.
    """,
    "description": """
        Partner-side module for client analytics.
        Receives analytics reports from client instances,
        stores them, provides a management dashboard,
        and supports configurable per-client alert rules.
    """,
    "license": "LGPL-3",
    "author": "LIDALabs",
    "website": "https://lidalabs.com",
    "category": "Technical",
    "version": "17.0.1.0.0",
    "depends": ["base", "mail"],
    "data": [
        "security/analytics_security.xml",
        "security/ir.model.access.csv",
        "views/analytics_client_views.xml",
        "views/analytics_report_views.xml",
        "views/analytics_alert_views.xml",
        "views/analytics_report_modules_views.xml",
        "views/menu.xml",
        "data/ir_cron.xml",
    ],
    "auto_install": False,
}
