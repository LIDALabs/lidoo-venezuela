from odoo import _, api, fields, models
from odoo.tools.sql import column_exists, create_column


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_igtf = fields.Boolean(readonly=True, store=True, compute="_compute_is_igtf")

    @api.depends('currency_id', 'type')
    def _compute_is_igtf(self):
        for rec in self:
            rec.is_igtf = rec.type and rec.currency_id and \
                rec.type in ['cash', 'bank'] and not rec.currency_id.name.startswith("VE")
