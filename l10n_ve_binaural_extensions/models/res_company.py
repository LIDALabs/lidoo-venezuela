import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"

    def _localization_use_documents(self):
        self.ensure_one()
        return self.account_fiscal_country_id.code == "VE" or super(ResCompany, self)._localization_use_documents()


