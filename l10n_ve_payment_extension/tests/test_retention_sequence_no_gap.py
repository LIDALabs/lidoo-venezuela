from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "retention_sequence")
class TestRetentionSequenceNoGap(TransactionCase):
    def test_no_gap_sequence_rolls_back(self):
        sequence = self.env["ir.sequence"].create(
            {
                "name": "No gap rollback test",
                "code": "retention.no_gap.rollback.test",
                "implementation": "no_gap",
                "number_next": 1,
                "padding": 8,
            }
        )
        initial_number = sequence.number_next_actual

        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                sequence.next_by_id()
                raise ValidationError("rollback test")

        self.env.invalidate_all()
        self.assertEqual(sequence.number_next_actual, initial_number)
