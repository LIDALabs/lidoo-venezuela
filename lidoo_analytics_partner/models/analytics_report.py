import json
from odoo import fields, models, api


class LidooAnalyticsReport(models.Model):
    _name = "lidoo.analytics.report"
    _description = "Analytics Report"
    _order = "report_date desc"

    client_id = fields.Many2one(
        "lidoo.analytics.client",
        string="Client",
        required=True,
        ondelete="cascade",
        index=True,
    )
    report_date = fields.Datetime(
        string="Report Date",
        default=fields.Datetime.now,
        readonly=True,
        index=True,
    )
    odoo_version = fields.Char(
        string="Odoo Version",
        readonly=True,
    )
    uptime_seconds = fields.Integer(
        string="Uptime (seconds)",
        readonly=True,
    )
    database_size = fields.Integer(
        string="Database Size (bytes)",
        readonly=True,
    )
    active_user_count = fields.Integer(
        string="Active Users",
        readonly=True,
    )
    installed_modules = fields.Text(
        string="Installed Modules (JSON)",
        readonly=True,
    )
    os_info = fields.Char(
        string="OS Info",
        readonly=True,
    )
    python_version = fields.Char(
        string="Python Version",
        readonly=True,
    )
    custom_module_count = fields.Integer(
        string="Custom Modules",
        readonly=True,
    )
    cpu_usage = fields.Float(
        string="CPU Usage (%)",
        readonly=True,
    )
    memory_usage = fields.Float(
        string="Memory Usage (%)",
        readonly=True,
    )
    raw_payload = fields.Text(
        string="Raw Payload (JSON)",
        readonly=True,
    )
    lidoo_commit_hash = fields.Char(
        string="Lidoo Commit",
        readonly=True,
        help="Último commit del repo lidoo (hash - mensaje | fecha)",
    )

    # Formatted helpers for UI
    uptime_display = fields.Char(
        string="Uptime",
        compute="_compute_uptime_display",
    )
    database_size_display = fields.Char(
        string="Database Size",
        compute="_compute_database_size_display",
    )

    module_ids = fields.One2many(
        "lidoo.analytics.report.modules",
        "report_id",
        string="Installed Modules",
        compute="_compute_module_ids",
        store=True
    )
    lidoo_module_ids = fields.One2many(
        "lidoo.analytics.report.modules",
        "report_id",
        string="Lidoo Modules",
        compute="_compute_lidoo_module_ids",
        store=True
    )

    def _compute_uptime_display(self):
        for record in self:
            seconds = record.uptime_seconds or 0
            days = seconds // 86400
            hours = (seconds % 86400) // 3600
            minutes = (seconds % 3600) // 60
            record.uptime_display = f"{days}d {hours}h {minutes}m"

    def _compute_database_size_display(self):
        for record in self:
            size = record.database_size or 0
            if size >= 1073741824:  # 1 GB
                record.database_size_display = f"{size / 1073741824:.2f} GB"
            elif size >= 1048576:  # 1 MB
                record.database_size_display = f"{size / 1048576:.2f} MB"
            elif size >= 1024:
                record.database_size_display = f"{size / 1024:.2f} KB"
            else:
                record.database_size_display = f"{size} B"


    @api.depends('installed_modules')
    def _compute_module_ids(self):
        for record in self:
            record.module_ids.unlink()
        
            modules_data = json.loads(record.installed_modules or "[]")
            
            for mod in modules_data:
                self.env['lidoo.analytics.report.modules'].create({
                    'report_id': record.id,
                    'name': mod.get('name', ''),
                    'version': mod.get('version', ''),
                })

    @api.depends('module_ids')
    def _compute_lidoo_module_ids(self):
        for record in self:
            record.lidoo_module_ids = record.module_ids.filtered(
                lambda m: m.name.startswith('l10n_ve_') or m.name.startswith('lidoo_')
            )