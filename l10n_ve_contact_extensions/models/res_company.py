from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    validate_user_creation_general = fields.Boolean(default=True)
