import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    group_sales_invoicing_series = fields.Boolean(default=True, readonly=True)

    def init(self):
        super().init()

        self.env.cr.execute("""
            UPDATE res_company
            SET group_sales_invoicing_series = true
        """)
