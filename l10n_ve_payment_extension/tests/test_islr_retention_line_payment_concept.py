# Copyright 2026 l10n_ve_payment_extension
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged, TransactionCase

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install", "l10n_ve_payment_extension")
class TestAccountRetentionLineISLRPaymentConcept(TransactionCase):
    """
    Tests for the ISLR retention line computed fields when the payment
    concept does not have a line matching the partner's type of person.

    Before this fix, the compute silently fell back to
    ``tax_unit.value * SENIAT_FACTOR_PN`` as ``related_pay_from`` when no
    matching line was found, producing a bogus base and a 0.00 retained
    amount with no visible error. The expected behaviour is to raise a
    ``UserError`` pointing to the missing configuration.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test ISLR Partner", "customer_rank": 1}
        )

    def _build_islr_line(self, payment_concept):
        """Build (in memory) a minimal ISLR retention line for testing."""
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test line",
                            "quantity": 1,
                            "price_unit": 100.0,
                        }
                    )
                ],
            }
        )
        return self.env["account.retention.line"].new(
            {
                "name": "ISLR Retention",
                "move_id": move,
                "payment_concept_id": payment_concept.id,
            }
        )

    def test_compute_raises_usererror_when_no_matching_type_person(self):
        """
        A payment concept with NO line for the partner's type of person
        must raise UserError, not silently produce a 0.00 retention.
        """
        # Ensure the partner has a type_person_id set.
        type_person = self.env["type.person"].search(
            [("state", "=", True)], limit=1
        )
        self.assertTrue(type_person, "Test requires at least one active type.person")
        self.partner.write({"type_person_id": type_person.id})

        # Build a payment concept whose only line is for a DIFFERENT
        # type of person (or with no type_person_id at all).
        other_type = self.env["type.person"].search(
            [("id", "!=", type_person.id), ("state", "=", True)], limit=1
        )
        if not other_type:
            # Fall back: create a second type.person for the test.
            other_type = self.env["type.person"].create(
                {"name": "Other type (test)", "state": True}
            )

        # Create a tariff required by the concept line.
        tariff = self.env["fees.retention"].create(
            {
                "name": "Tariff test 5%",
                "percentage": 5.0,
                "tax_unit_ids": self.env["tax.unit"].search(
                    [("status", "=", True)], limit=1
                ).id,
            }
        )

        concept = self.env["payment.concept"].create(
            {
                "name": "Concept without line for partner type",
                "line_payment_concept_ids": [
                    Command.create(
                        {
                            "code": "9999",
                            "type_person_id": other_type.id,
                            "pay_from": 0.0,
                            "percentage_tax_base": 100.0,
                            "tariff_id": tariff.id,
                        }
                    )
                ],
            }
        )

        line = self._build_islr_line(concept)

        with self.assertRaises(UserError) as cm:
            line._compute_related_fields()
        msg = str(cm.exception)
        self.assertIn(concept.name, msg)
        self.assertIn(self.partner.name, msg)
        self.assertIn(type_person.name, msg)

    def test_compute_does_not_raise_when_type_person_matches(self):
        """
        Happy path: when the payment concept has a line for the
        partner's type of person, the compute must populate
        ``related_pay_from`` and not raise.
        """
        type_person = self.env["type.person"].search(
            [("state", "=", True)], limit=1
        )
        self.assertTrue(type_person)
        self.partner.write({"type_person_id": type_person.id})

        tariff = self.env["fees.retention"].create(
            {
                "name": "Tariff happy path",
                "percentage": 5.0,
                "tax_unit_ids": self.env["tax.unit"].search(
                    [("status", "=", True)], limit=1
                ).id,
            }
        )

        concept = self.env["payment.concept"].create(
            {
                "name": "Concept with matching line",
                "line_payment_concept_ids": [
                    Command.create(
                        {
                            "code": "8888",
                            "type_person_id": type_person.id,
                            "pay_from": 0.0,
                            "percentage_tax_base": 100.0,
                            "tariff_id": tariff.id,
                        }
                    )
                ],
            }
        )

        line = self._build_islr_line(concept)
        # Must not raise.
        line._compute_related_fields()
        self.assertGreater(line.related_pay_from, 0.0)
