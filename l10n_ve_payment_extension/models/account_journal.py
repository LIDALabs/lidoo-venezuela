from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    default_account_id = fields.Many2one(
        domain=(
            "[('deprecated', '=', False), ('company_id', '=', company_id),"
            "'|',('account_type', '=', default_account_type),"
            "('account_type', 'in', ('income', 'income_other') if type == 'sale' else ('expense', 'expense_depreciation', 'expense_direct_cost') if type == 'purchase' else ('asset_current', 'liability_current'))]"
        )
    )

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
