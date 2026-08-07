from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "iva_retention_reversal")
class TestSupplierIvaRetentionReversal(TransactionCase):
    """Focused regression checks for supplier credit-note reversals."""

    def _find_fixture(self):
        refunds = self.env["account.move"].search(
            [
                ("move_type", "=", "in_refund"),
                ("state", "=", "posted"),
                ("reversed_entry_id", "!=", False),
            ],
            order="id",
        )
        for refund in refunds:
            original = refund.reversed_entry_id
            retention = self.env["account.retention"].search(
                [
                    ("type_retention", "=", "iva"),
                    ("type", "=", "in_invoice"),
                    ("state", "=", "emitted"),
                    ("partner_id", "=", original.partner_id.id),
                    ("retention_line_ids.move_id", "=", original.id),
                ],
                limit=1,
            )
            if retention:
                return original, refund, retention
        self.skipTest("No posted supplier credit note with an emitted IVA retention fixture")

    def test_credit_note_uses_positive_line_values(self):
        original, refund, original_retention = self._find_fixture()
        line_data = self.env["account.retention"].compute_retention_lines_data(refund)

        self.assertTrue(line_data)
        self.assertTrue(all(line["retention_amount"] > 0 for line in line_data))
        self.assertEqual(line_data[0]["invoice_type"], "in_refund")
        self.assertAlmostEqual(
            sum(line["retention_amount"] for line in line_data),
            abs(original_retention.total_retention_amount),
            delta=0.01,
        )
        self.assertEqual(original.move_type, "in_invoice")

    def test_credit_note_creates_and_reuses_reversal(self):
        _original, refund, original_retention = self._find_fixture()
        reversal = refund._create_supplier_iva_retention_reversal()

        self.assertTrue(reversal)
        self.assertEqual(reversal.reversal_of_id, original_retention)
        self.assertEqual(reversal.type_retention, "iva")
        self.assertEqual(reversal.type, "in_invoice")
        self.assertIn(reversal.state, ("draft", "emitted"))
        self.assertEqual(reversal.retention_line_ids.mapped("move_id"), refund)

        payment = reversal.payment_ids
        self.assertEqual(payment.payment_type, "inbound")
        self.assertTrue(payment.payment_method_line_id)
        self.assertAlmostEqual(
            payment.amount,
            abs(original_retention.total_retention_amount),
            delta=0.01,
        )

        self.assertEqual(refund._create_supplier_iva_retention_reversal(), reversal)

        if reversal.state == "draft":
            reversal.action_post()
        self.assertEqual(reversal.state, "emitted")
        self.assertEqual(payment.state, "posted")
        self.assertTrue(payment.move_id)
        self.assertEqual(refund.iva_voucher_number, reversal.number)

        retained_account = payment.journal_id.default_account_id
        retained_lines = payment.move_id.line_ids.filtered(
            lambda line: line.account_id == retained_account
        )
        self.assertTrue(any(line.debit > 0 for line in retained_lines))
        payable_lines = refund.line_ids.filtered(
            lambda line: line.account_id.account_type == "liability_payable"
        )
        self.assertTrue(payable_lines.reconciled)
