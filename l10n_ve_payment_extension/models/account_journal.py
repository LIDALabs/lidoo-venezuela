from odoo import api, fields, models
from odoo.exceptions import UserError


RETENTION_SEQUENCE_REGEX = {
    "iva": (
        r"^(?P<prefix1>RIV-)"
        r"(?P<year>(?:19|20|21)\d{2})"
        r"(?P<month>0[1-9]|1[0-2])"
        r"(?P<seq>\d{8})"
        r"(?P<suffix>-.*)$"
    ),
    "islr": (
        r"^(?P<prefix1>RIS-)"
        r"(?P<year>(?:19|20|21)\d{2})"
        r"(?P<month>0[1-9]|1[0-2])"
        r"(?P<seq>\d{5})"
        r"(?P<suffix>-.*)$"
    ),
    "municipal": (
        r"^(?P<prefix1>RM-)"
        r"(?P<year>(?:19|20|21)\d{2})"
        r"(?P<month>0[1-9]|1[0-2])"
        r"(?P<seq>\d{5})"
        r"(?P<suffix>-.*)$"
    ),
}


class AccountJournal(models.Model):
    _inherit = "account.journal"

    default_account_id = fields.Many2one(
        domain=(
            "[('deprecated', '=', False), ('company_id', '=', company_id),"
            "'|',('account_type', '=', default_account_type),"
            "('account_type', 'in', ('income', 'income_other') if type == 'sale' else ('expense', 'expense_depreciation', 'expense_direct_cost') if type == 'purchase' else ('asset_current', 'liability_current'))]"
        )
    )

    @api.model
    def _clear_retention_sequence_overrides(self):
        """Remove the journal-wide regex from the previous implementation.

        ``sequence_override_regex`` applies to every move in a journal, while
        retention payment moves have a temporary name during creation. The
        retention-specific parser now lives on ``account.move`` instead.
        Only the exact regexes introduced by this module are cleared.
        """
        retention_regexes = tuple(RETENTION_SEQUENCE_REGEX.values())
        journals = self.search([
            ("sequence_override_regex", "in", retention_regexes),
        ])
        journals.write({"sequence_override_regex": False})

    def _ensure_retention_payment_method_line(self, payment_type):
        """Return a direction-compatible retention method line.

        Supplier retention journals are historically configured only for outbound
        payments. A supplier credit-note reversal is an inbound technical payment,
        so create the missing counterpart using the same retained-IVA account.
        """
        self.ensure_one()
        if payment_type not in ("inbound", "outbound"):
            raise UserError(
                "The retention payment type must be inbound or outbound."
            )

        method_lines = (
            self.inbound_payment_method_line_ids
            if payment_type == "inbound"
            else self.outbound_payment_method_line_ids
        )
        if method_lines:
            return method_lines[0]

        opposite_lines = (
            self.outbound_payment_method_line_ids
            if payment_type == "inbound"
            else self.inbound_payment_method_line_ids
        )
        payment_account = opposite_lines.mapped("payment_account_id")[:1]
        payment_account = payment_account or self.default_account_id
        if not payment_account:
            raise UserError(
                "The retention journal must have an account before creating "
                "a reversal payment."
            )

        payment_method_xmlid = (
            "account.account_payment_method_manual_in"
            if payment_type == "inbound"
            else "account.account_payment_method_manual_out"
        )
        return self.env["account.payment.method.line"].create(
            {
                "name": "Reversión de retención de IVA"
                if payment_type == "inbound"
                else "Retención de IVA",
                "payment_method_id": self.env.ref(payment_method_xmlid).id,
                "payment_account_id": payment_account.id,
                "journal_id": self.id,
            }
        )
