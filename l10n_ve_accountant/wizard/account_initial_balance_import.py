import csv
import io
import base64
import logging
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    import xlrd
except ImportError:
    xlrd = None
    _logger.debug("xlrd not available, XLS import disabled")

try:
    import xlwt
except ImportError:
    xlwt = None
    _logger.debug("xlwt not available, XLS template export disabled")


class AccountInitialBalanceImport(models.TransientModel):
    _name = "account.initial.balance.import"
    _description = "Import Initial Account Balances"
    _check_company_auto = True

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company.id,
        readonly=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        domain="[('type', '=', 'general'), ('company_id', '=', company_id)]",
        default=lambda self: self._find_initial_balance_journal(),
        readonly=True,
        help="General journal for initial balance entries",
    )

    @api.model
    def _find_initial_balance_journal(self):
        """Find the journal for initial balances (saldos iniciales)."""
        company = self.env.company
        journal = self.env["account.journal"].search([
            ("type", "=", "general"),
            ("company_id", "=", company.id),
            ("name", "ilike", "saldos iniciales"),
        ], limit=1)
        if not journal:
            journal = self.env["account.journal"].search([
                ("type", "=", "general"),
                ("company_id", "=", company.id),
            ], limit=1)
        return journal.id if journal else False

    @api.constrains("journal_id")
    def _check_journal_type(self):
        for record in self:
            if record.journal_id and record.journal_id.type != "general":
                raise ValidationError(
                    _("The journal must be of type 'General' for initial balance entries.")
                )

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
        help="Date for the initial balance entries",
    )
    file = fields.Binary(
        string="File",
        help="CSV or XLS file with initial balances",
    )
    filename = fields.Char(string="File Name")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("validated", "Validated"),
            ("done", "Done"),
        ],
        string="State",
        default="draft",
        readonly=True,
    )
    line_ids = fields.One2many(
        "account.initial.balance.import.line",
        "wizard_id",
        string="Import Lines",
        readonly=True,
    )
    error_count = fields.Integer(
        string="Errors",
        compute="_compute_counts",
    )
    warning_count = fields.Integer(
        string="Warnings",
        compute="_compute_counts",
    )
    valid_count = fields.Integer(
        string="Valid Lines",
        compute="_compute_counts",
    )
    move_id = fields.Many2one(
        "account.move",
        string="Journal Entry",
        readonly=True,
        help="Created journal entry",
    )

    @api.depends("line_ids", "line_ids.state")
    def _compute_counts(self):
        for record in self:
            record.error_count = len(record.line_ids.filtered(lambda l: l.state == "error"))
            record.warning_count = len(record.line_ids.filtered(lambda l: l.state == "warning"))
            record.valid_count = len(record.line_ids.filtered(lambda l: l.state == "valid"))

    def _parse_csv(self, data):
        """Parse CSV file and return rows."""
        decoded = base64.b64decode(data)
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                content = decoded.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise UserError(_("Unable to decode the file. Please use UTF-8 or Latin-1 encoding."))

        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        if not rows:
            raise UserError(_("The file is empty."))
        return rows

    def _parse_xls(self, data):
        """Parse XLS file and return rows with string values.

        Uses xlrd row_values() which returns native types:
        - NUMBER cells → float
        - All others → string or empty
        """
        if xlrd is None:
            raise UserError(
                _("XLS import requires xlrd. Install it: pip install xlrd")
            )

        decoded = base64.b64decode(data)
        wb = xlrd.open_workbook(file_contents=decoded)
        ws = wb.sheet_by_index(0)

        rows = []
        for row_idx in range(ws.nrows):
            raw_row = ws.row_values(row_idx)
            _logger.info("XLS row %d raw: %s", row_idx, raw_row)
            rows.append(raw_row)

        return rows

    def _get_required_columns(self):
        """Return the list of required column names."""
        return [
            "Account Code",
            "Debit",
            "Credit",
        ]

    def _get_optional_columns(self):
        """Return the list of optional column names."""
        return [
            "Partner",
            "Partner Tax ID",
            "Currency",
            "Amount Currency",
            "Reference",
            "Description",
            "Analytic Account",
            "Tax",
        ]

    def _get_all_columns(self):
        """Return all supported columns."""
        return self._get_required_columns() + self._get_optional_columns()

    def _validate_header(self, header):
        """Validate the CSV/XLS header row."""
        required = self._get_required_columns()
        normalized_header = [str(h).strip() for h in header]

        missing_required = [col for col in required if col not in normalized_header]
        if missing_required:
            raise UserError(
                _("Missing required columns: %s\n\n"
                  "Required columns: %s\n"
                  "Optional columns: %s")
                % (", ".join(missing_required), ", ".join(required), ", ".join(self._get_optional_columns()))
            )

        _logger.info("Header validated: %s", normalized_header)
        return normalized_header

    def _find_account(self, code):
        """Find account by code."""
        account = self.env["account.account"].search(
            [("code", "=", code), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        return account

    def _find_partner(self, name=None, vat=None):
        """Find partner by name or VAT."""
        if vat:
            partner = self.env["res.partner"].search(
                [("vat", "=", vat), ("company_id", "=", self.env.company.id)],
                limit=1,
            )
            if partner:
                return partner
        if name:
            partner = self.env["res.partner"].search(
                [("name", "ilike", name), ("company_id", "=", self.env.company.id)],
                limit=1,
            )
            return partner
        return False

    def _find_currency(self, code):
        """Find currency by code."""
        if not code or code.upper() in ("VEF", "VES"):
            return self.env.company.currency_id
        currency = self.env["res.currency"].search(
            [("name", "=ilike", code.strip())],
            limit=1,
        )
        return currency or self.env.company.currency_id

    def _find_analytic_account(self, name):
        """Find analytic account by name."""
        if not name:
            return False
        analytic = self.env["account.analytic.account"].search(
            [("name", "ilike", name), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        return analytic

    def _find_tax(self, name):
        """Find tax by name."""
        if not name:
            return False
        tax = self.env["account.tax"].search(
            [("name", "ilike", name), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        return tax

    def action_validate(self):
        """Parse the file and validate lines."""
        self.ensure_one()

        if not self.file:
            raise UserError(_("Please upload a file first."))

        filename = self.filename or ""
        if filename.lower().endswith(".csv"):
            rows = self._parse_csv(self.file)
        elif filename.lower().endswith((".xls", ".xlsx")):
            rows = self._parse_xls(self.file)
        else:
            raise UserError(
                _("Unsupported file format. Please upload a CSV or XLS/XLSX file.")
            )

        if len(rows) < 2:
            raise UserError(
                _("The file must have a header row and at least one data row.")
            )

        header = rows[0]
        normalized_header = self._validate_header(header)
        col_map = {col: idx for idx, col in enumerate(normalized_header)}

        _logger.info("COLUMN MAP: %s", col_map)
        _logger.info("First data row: %s", rows[1] if len(rows) > 1 else "NONE")

        self.line_ids.unlink()

        Line = self.env["account.initial.balance.import.line"]
        errors = []

        for row_num, row in enumerate(rows[1:], start=2):
            # Skip fully empty rows
            if not any(cell for cell in row):
                continue

            def get_val(col_name, default=""):
                idx = col_map.get(col_name)
                if idx is not None and idx < len(row):
                    return str(row[idx]).strip() if row[idx] is not None else ""
                return default

            account_code = get_val("Account Code")
            debit_str = get_val("Debit", "0")
            credit_str = get_val("Credit", "0")

            _logger.info(
                "Row %d: account_code=%r debit_str=%r credit_str=%r (raw row=%s)",
                row_num, account_code, debit_str, credit_str, row
            )

            if not account_code:
                errors.append(f"Row {row_num}: Account Code is required")
                continue

            account = self._find_account(account_code)
            if not account:
                errors.append(f"Row {row_num}: Account '{account_code}' not found")
                continue

            try:
                debit = float(debit_str.replace(",", ".")) if debit_str else 0.0
            except ValueError:
                errors.append(f"Row {row_num}: Invalid Debit amount '{debit_str}'")
                continue

            try:
                credit = float(credit_str.replace(",", ".")) if credit_str else 0.0
            except ValueError:
                errors.append(f"Row {row_num}: Invalid Credit amount '{credit_str}'")
                continue

            _logger.info("Row %d: parsed debit=%s credit=%s", row_num, debit, credit)

            if debit == 0 and credit == 0:
                errors.append(f"Row {row_num}: Both Debit and Credit are zero")
                continue

            if debit < 0 or credit < 0:
                errors.append(f"Row {row_num}: Amounts cannot be negative")
                continue

            partner = self._find_partner(
                name=get_val("Partner"),
                vat=get_val("Partner Tax ID"),
            )
            currency = self._find_currency(get_val("Currency"))
            analytic = self._find_analytic_account(get_val("Analytic Account"))
            tax = self._find_tax(get_val("Tax"))

            state = "valid"
            notes = []

            if not partner and get_val("Partner"):
                state = "warning"
                notes.append(f"Partner '{get_val('Partner')}' not found")

            if not analytic and get_val("Analytic Account"):
                state = "warning"
                notes.append(f"Analytic Account '{get_val('Analytic Account')}' not found")

            if not tax and get_val("Tax"):
                state = "warning"
                notes.append(f"Tax '{get_val('Tax')}' not found")

            line_vals = {
                "wizard_id": self.id,
                "row_number": row_num,
                "account_id": account.id,
                "account_code": account_code,
                "partner_id": partner.id if partner else False,
                "partner_name": get_val("Partner"),
                "partner_vat": get_val("Partner Tax ID"),
                "currency_id": currency.id if currency else False,
                "debit": debit,
                "credit": credit,
                "amount_currency": float(get_val("Amount Currency", "0").replace(",", ".")) if get_val("Amount Currency") else 0.0,
                "reference": get_val("Reference"),
                "description": get_val("Description"),
                "analytic_account_id": analytic.id if analytic else False,
                "analytic_name": get_val("Analytic Account"),
                "tax_id": tax.id if tax else False,
                "tax_name": get_val("Tax"),
                "state": state,
                "notes": "; ".join(notes) if notes else False,
            }

            Line.create(line_vals)

        if errors:
            raise UserError(
                _("Validation errors found:\n\n%s") % "\n".join(errors)
            )

        if not self.line_ids:
            raise UserError(_("No valid lines found in the file."))

        total_debit = sum(self.line_ids.mapped("debit"))
        total_credit = sum(self.line_ids.mapped("credit"))
        _logger.info("Balance check: total_debit=%s total_credit=%s", total_debit, total_credit)
        if abs(total_debit - total_credit) > 0.01:
            raise UserError(
                _("Journal entry is not balanced!\n\n"
                  "Total Debit: %.2f\n"
                  "Total Credit: %.2f\n"
                  "Difference: %.2f\n\n"
                  "Please adjust your file to balance the entry.")
                % (total_debit, total_credit, abs(total_debit - total_credit))
            )

        self.state = "validated"
        self.env.flush_all()

        # Create the move first (without lines)
        move_vals = {
            "journal_id": self.journal_id.id,
            "date": self.date,
            "move_type": "entry",
            "ref": "Initial Balance Import",
            "company_id": self.company_id.id,
            "state": "draft",
        }
        move = self.env["account.move"].create(move_vals)

        # Create move lines with explicit move_id
        line_vals_list = []
        for line in self.line_ids:
            _logger.info(
                "Creating move line: account=%s debit=%s credit=%s",
                line.account_code, line.debit, line.credit
            )
            line_vals = {
                "move_id": move.id,
                "account_id": line.account_id.id,
                "debit": line.debit,
                "credit": line.credit,
                "partner_id": line.partner_id.id if line.partner_id else False,
                "name": line.description or line.reference or f"Initial Balance - {line.account_code}",
                "analytic_distribution": {line.analytic_account_id.id: 100} if line.analytic_account_id else False,
            }

            # Only set currency/amount_currency for foreign currencies
            # DO NOT pass currency_id=False or amount_currency=0.0 for company currency
            # because l10n_ve_accountant's _inverse_amount_currency overwrites balance=amount_currency
            if line.currency_id and line.currency_id != self.env.company.currency_id:
                line_vals["currency_id"] = line.currency_id.id
                line_vals["amount_currency"] = line.amount_currency

            if line.tax_id:
                line_vals["tax_ids"] = [(6, 0, [line.tax_id.id])]

            line_vals_list.append(line_vals)

        if line_vals_list:
            created_lines = self.env["account.move.line"].create(line_vals_list)
            _logger.info("Created %d move lines with IDs: %s", len(created_lines), created_lines.ids)

        self.move_id = move
        self.state = "done"

        return {
            "type": "ir.actions.act_window",
            "name": "Journal Entry",
            "res_model": "account.move",
            "res_id": move.id,
            "view_mode": "form",
            "target": "current",
        }


    def action_download_template(self):
        """Download an XLS template for initial balance import."""
        if xlwt is None:
            raise UserError(
                _("XLS template requires xlwt. Install it: pip install xlwt. "
                  "Alternatively, use CSV format instead.")
            )

        header = self._get_all_columns()

        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Saldos Iniciales')

        # Header style
        header_style = xlwt.easyxf(
            'font: bold on, color white;'
            'pattern: pattern solid, fore_colour ocean_blue;'
            'alignment: horizontal center;'
        )

        # Write header
        for col_idx, col_name in enumerate(header):
            ws.write(0, col_idx, col_name, header_style)

        # Example rows - write numbers as actual numeric values
        example1 = [
            "1.1.1.01.001",  # Código de Cuenta
            1000.00,          # Débito (número)
            "",               # Crédito
            "Proveedor Ejemplo",
            "V-12345678",
            "USD",
            "",
            "REF-001",
            "Saldo inicial",
            "",
            "",
        ]
        example2 = [
            "2.1.1.01.001",  # Código de Cuenta
            "",               # Débito
            1000.00,          # Crédito (número)
            "Cliente Ejemplo",
            "V-87654321",
            "USD",
            "",
            "REF-002",
            "Saldo inicial - Cuentas por Pagar",
            "",
            "",
        ]
        for row_idx, row_data in enumerate([example1, example2], start=1):
            for col_idx, value in enumerate(row_data):
                if isinstance(value, (int, float)):
                    ws.write(row_idx, col_idx, value)  # escribe como NUMBER
                else:
                    ws.write(row_idx, col_idx, value)  # escribe como TEXT / label

        # Documentation style
        required_style = xlwt.easyxf('font: bold on, color red;')
        optional_style = xlwt.easyxf('font: bold on, color ocean_blue;')

        # Documentation rows
        doc_row = 4
        ws.write(doc_row, 0, "COLUMNAS REQUERIDAS:", required_style)
        doc_row += 1
        ws.write(doc_row, 0, "Código de Cuenta: El código de la cuenta del Plan de Cuentas (ej: 1.1.1.01.001)")
        doc_row += 1
        ws.write(doc_row, 0, "Débito: El monto de débito (dejar vacío si es crédito)")
        doc_row += 1
        ws.write(doc_row, 0, "Crédito: El monto de crédito (dejar vacío si es débito)")
        doc_row += 2
        ws.write(doc_row, 0, "COLUMNAS OPCIONALES:", optional_style)
        doc_row += 1
        ws.write(doc_row, 0, "Proveedor/Cliente: El nombre del tercero (se buscará en el sistema)")
        doc_row += 1
        ws.write(doc_row, 0, "RIF/Cédula: El RIF o Cédula del tercero (preferido para coincidencia)")
        doc_row += 1
        ws.write(doc_row, 0, "Moneda: Código de moneda (ej: USD, VES)")
        doc_row += 1
        ws.write(doc_row, 0, "Monto Moneda: Monto en moneda extranjera")
        doc_row += 1
        ws.write(doc_row, 0, "Referencia: Referencia del documento")
        doc_row += 1
        ws.write(doc_row, 0, "Descripción: Descripción de la línea")
        doc_row += 1
        ws.write(doc_row, 0, "Cuenta Analítica: Nombre de la cuenta analítica")
        doc_row += 1
        ws.write(doc_row, 0, "Impuesto: Nombre del impuesto")

        # Save to buffer
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        content = output.getvalue()
        output.close()

        attachment = self.env["ir.attachment"].create({
            "name": "plantilla_saldos_iniciales.xls",
            "type": "binary",
            "datas": base64.b64encode(content),
            "res_model": "account.initial.balance.import",
            "res_id": self.id,
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }


class AccountInitialBalanceImportLine(models.TransientModel):
    _name = "account.initial.balance.import.line"
    _description = "Initial Balance Import Line"
    _check_company_auto = True

    wizard_id = fields.Many2one(
        "account.initial.balance.import",
        string="Wizard",
        required=True,
        ondelete="cascade",
    )
    row_number = fields.Integer(string="Row", readonly=True)
    account_id = fields.Many2one(
        "account.account",
        string="Account",
        required=True,
        readonly=True,
    )
    account_code = fields.Char(string="Account Code", readonly=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        readonly=True,
    )
    partner_name = fields.Char(string="Partner Name", readonly=True)
    partner_vat = fields.Char(string="Partner Tax ID", readonly=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        readonly=True,
    )
    debit = fields.Float(string="Debit", readonly=True)
    credit = fields.Float(string="Credit", readonly=True)
    amount_currency = fields.Float(string="Amount Currency", readonly=True)
    reference = fields.Char(string="Reference", readonly=True)
    description = fields.Char(string="Description", readonly=True)
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        readonly=True,
    )
    analytic_name = fields.Char(string="Analytic Name", readonly=True)
    tax_id = fields.Many2one(
        "account.tax",
        string="Tax",
        readonly=True,
    )
    tax_name = fields.Char(string="Tax Name", readonly=True)
    state = fields.Selection(
        [
            ("valid", "Valid"),
            ("warning", "Warning"),
            ("error", "Error"),
        ],
        string="State",
        readonly=True,
    )
    notes = fields.Text(string="Notes", readonly=True)
