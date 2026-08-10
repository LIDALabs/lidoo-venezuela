from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "retention_sequence")
class TestRetentionSequenceFormat(TransactionCase):
    def _create_journal(self, code):
        return self.env["account.journal"].create(
            {
                "name": f"{code} retention test journal",
                "code": code,
                "type": "general",
                "company_id": self.env.company.id,
            }
        )

    def test_supplier_invoice_number_is_an_opaque_suffix(self):
        samples = (
            ("iva", "RIV", "00000060"),
            ("islr", "RIS", "00060"),
            ("municipal", "RM", "00060"),
        )
        supplier_invoice_number = "F 01C10000000250589020"

        for retention_type, prefix, sequence_number in samples:
            with self.subTest(retention_type=retention_type):
                journal = self._create_journal(prefix)
                payment = self.env["account.payment"].new(
                    {
                        "is_retention": True,
                        "payment_type_retention": retention_type,
                    }
                )
                move = self.env["account.move"].new(
                    {
                        "name": (
                            f"{prefix}-202608{sequence_number}-"
                            f"{supplier_invoice_number}"
                        ),
                        "date": date(2026, 8, 10),
                        "journal_id": journal.id,
                        "payment_id": payment,
                        "state": "posted",
                    }
                )

                self.assertFalse(journal.sequence_override_regex)
                self.assertTrue(move._sequence_matches_date())
                move._compute_split_sequence()
                self.assertEqual(move.sequence_number, int(sequence_number))
                self.assertEqual(move.sequence_prefix, f"{prefix}-202608")

    def test_date_validation_is_still_active(self):
        journal = self._create_journal("RIVT")
        payment = self.env["account.payment"].new(
            {
                "is_retention": True,
                "payment_type_retention": "iva",
            }
        )
        move = self.env["account.move"].new(
            {
                "name": "RIV-20260700000060-F 01C10000000250589020",
                "date": date(2026, 8, 10),
                "journal_id": journal.id,
                "payment_id": payment,
                "state": "posted",
            }
        )

        self.assertFalse(move._sequence_matches_date())

    def test_temporary_payment_name_uses_native_parser(self):
        journal = self._create_journal("RIVT")
        payment = self.env["account.payment"].new(
            {
                "is_retention": True,
                "payment_type_retention": "iva",
            }
        )
        move = self.env["account.move"].new(
            {
                "name": "/",
                "date": date(2026, 8, 10),
                "journal_id": journal.id,
                "payment_id": payment,
                "state": "draft",
            }
        )

        move._compute_split_sequence()
        self.assertEqual(move.sequence_number, 0)
