import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class IrSequence(models.Model):
    _inherit = "ir.sequence"

    journals_using_sequence_as_correlative_series_ids = fields.One2many(
        comodel_name='account.journal',
        inverse_name='series_correlative_sequence_id',
        string="Journals using this sequence as correlative series"
    )

    def unlink(self):
        for sequence in self:
            if sequence.journals_using_sequence_as_correlative_series_ids:
                raise UserError("Esta secuencia esta siendo utilizada para asignar números de control y no puede ser eliminada")

        return super(IrSequence, self).unlink()
