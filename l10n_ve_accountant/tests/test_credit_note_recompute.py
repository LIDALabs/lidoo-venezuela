from unittest.mock import patch

from odoo import Command, fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "l10n_ve_accountant")
class TestCreditNoteRecompute(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.foreign_currency = cls.company.currency_foreign_id
        if not cls.foreign_currency:
            cls.foreign_currency = cls.env.ref("base.USD")
            cls.company.write({"currency_foreign_id": cls.foreign_currency.id})
        if not cls.env["res.currency.rate"].search([
            ("currency_id", "=", cls.foreign_currency.id),
            ("company_id", "=", cls.company.id),
            ("name", "=", fields.Date.today()),
        ], limit=1):
            cls.env["res.currency.rate"].create({
                "name": fields.Date.today(),
                "currency_id": cls.foreign_currency.id,
                "rate": 1.0,
                "company_id": cls.company.id,
            })
        cls.receivable_account = cls.env["account.account"].create({
            "name": "Credit note test receivable",
            "code": "TCR001",
            "account_type": "asset_receivable",
            "reconcile": True,
            "company_id": cls.company.id,
        })
        cls.income_account = cls.env["account.account"].create({
            "name": "Credit note test income",
            "code": "TCI001",
            "account_type": "income",
            "company_id": cls.company.id,
        })
        cls.state = cls.env["res.country.state"].search([
            ("country_id", "=", cls.company.country_id.id),
        ], limit=1)
        cls.municipality = cls.env["res.country.municipality"].search([
            ("state_id", "in", cls.state.id),
        ], limit=1)
        cls.zip_code = cls.env[
            "res.country.municipality.zip.code"
        ].search([
            ("municipality_id", "=", cls.municipality.id),
        ], limit=1)
        cls.partner = cls.env["res.partner"].create({
            "name": "Credit note recompute partner",
            "street": "Credit note test street",
            "zip": "1010",
            "state_id": cls.state.id,
            "municipality": cls.municipality.id,
            "zip_code_id": cls.zip_code.id,
            "property_account_receivable_id": cls.receivable_account.id,
        })
        cls.sale_journal = cls.env["account.journal"].create({
            "name": "Credit note recompute sales",
            "code": "TCNR",
            "type": "sale",
            "company_id": cls.company.id,
            "default_account_id": cls.income_account.id,
            "series_correlative_sequence_id": cls.env[
                "ir.sequence"
            ].search([("code", "=", "series.invoice.correlative")], limit=1).id,
        })
        cls.tax = cls.env["account.tax"].create({
            "name": "Credit note test VAT 16%",
            "amount": 16.0,
            "amount_type": "percent",
            "type_tax_use": "sale",
            "company_id": cls.company.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Credit note taxable service",
            "type": "service",
            "property_account_income_id": cls.income_account.id,
            "taxes_id": [Command.set(cls.tax.ids)],
        })
        cls.payment_term = cls.env["account.payment.term"].create({
            "name": "Credit note test immediate payment",
            "company_id": cls.company.id,
        })

    def test_credit_note_needed_terms_do_not_recompute_tax_totals(self):
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner.id,
            "journal_id": self.sale_journal.id,
            "invoice_date": fields.Date.today(),
            "invoice_payment_term_id": self.payment_term.id,
            "invoice_line_ids": [
                Command.create({
                    "name": "Taxable service",
                    "product_id": self.product.id,
                    "account_id": self.income_account.id,
                    "quantity": 1.0,
                    "price_unit": 100.0,
                    "tax_ids": [Command.set(self.tax.ids)],
                }),
            ],
        })
        invoice.with_context(move_action_post_alert=True).action_post()
        credit_note = invoice._reverse_moves([{
            "date": fields.Date.today(),
            "invoice_date": fields.Date.today(),
            "invoice_payment_term_id": False,
        }])

        def forbidden_tax_totals_recompute(records):
            raise AssertionError(
                "_compute_needed_terms must not recompute tax_totals"
            )

        credit_note.invalidate_recordset([
            "needed_terms",
            "foreign_total_billed",
            "foreign_taxable_income",
            "tax_totals",
        ])
        with patch.object(
            type(credit_note),
            "_compute_tax_totals",
            forbidden_tax_totals_recompute,
        ):
            credit_note._compute_needed_terms()

        expected_foreign_total = sum(
            credit_note.invoice_line_ids.mapped("foreign_price_total")
        )
        needed_foreign_total = sum(
            values.get("foreign_balance", 0.0)
            for values in credit_note.needed_terms.values()
        )
        self.assertAlmostEqual(
            needed_foreign_total,
            -expected_foreign_total,
            places=2,
        )
        self.assertAlmostEqual(
            sum(credit_note.line_ids.mapped("debit")),
            sum(credit_note.line_ids.mapped("credit")),
            places=2,
        )
