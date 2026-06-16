# -*- coding: utf-8 -*-
import base64
import csv
import io
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    _logger.warning("openpyxl not installed. XLS import will not work.")
    openpyxl = None


class AccountChartReplaceWizard(models.TransientModel):
    _name = "account.chart.replace.wizard"
    _description = "Replace Chart of Accounts"

    file = fields.Binary(string="File", required=True)
    file_name = fields.Char(string="File Name")
    file_format = fields.Selection(
        selection=[("csv", "CSV"), ("xls", "XLS/XLSX")],
        string="Format",
        required=True,
        default="csv",
    )
    log = fields.Text(string="Log", readonly=True)

    @api.onchange("file_name")
    def _onchange_file_name(self):
        if self.file_name:
            if self.file_name.lower().endswith((".xls", ".xlsx")):
                self.file_format = "xls"
            elif self.file_name.lower().endswith(".csv"):
                self.file_format = "csv"

    def _parse_csv(self, data):
        """Parse CSV file and return list of dicts with 'code' and 'name'."""
        decoded = base64.b64decode(data)
        text = decoded.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text), delimiter=",")
        rows = []
        for row in reader:
            code = (row.get("code") or row.get("Code") or "").strip()
            name = (row.get("name") or row.get("Name") or "").strip()
            if code and name:
                rows.append({"code": code, "name": name})
        return rows

    def _parse_xls(self, data):
        """Parse XLS/XLSX file and return list of dicts with 'code' and 'name'."""
        if not openpyxl:
            raise UserError(_("The 'openpyxl' library is not installed. Cannot read XLS files."))
        decoded = base64.b64decode(data)
        wb = openpyxl.load_workbook(io.BytesIO(decoded), read_only=True, data_only=True)
        ws = wb.active
        rows = []
        header = None
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                # Detect header row — look for 'code' and 'name' columns
                header = [str(c).strip().lower() if c else "" for c in row]
                continue
            if not header:
                continue
            row_dict = {header[j]: str(row[j]).strip() if row[j] else "" for j in range(len(header))}
            code = row_dict.get("code", "")
            name = row_dict.get("name", "")
            if code and name:
                rows.append({"code": code, "name": name})
        wb.close()
        return rows

    def action_replace(self):
        """Main action: compare by code, update name if exists, create if not."""
        self.ensure_one()
        if not self.file:
            raise UserError(_("Please upload a file."))

        # Parse file
        if self.file_format == "csv":
            rows = self._parse_csv(self.file)
        else:
            rows = self._parse_xls(self.file)

        if not rows:
            raise UserError(_("No valid rows found. The file must have 'code' and 'name' columns."))

        Account = self.env["account.account"]
        Company = self.env.company

        # Pre-fetch existing accounts by code for performance
        existing_accounts = Account.search([("company_id", "=", Company.id)])
        code_map = {acc.code: acc for acc in existing_accounts}

        created = 0
        updated = 0
        skipped = 0
        created_lines = []
        updated_lines = []
        skipped_lines = []

        for row in rows:
            code = row["code"]
            name = row["name"]

            if code in code_map:
                acc = code_map[code]
                if acc.name != name:
                    old_name = acc.name
                    acc.write({"name": name})
                    updated += 1
                    updated_lines.append(f"  {code}: '{old_name}' -> '{name}'")
                else:
                    skipped += 1
                    skipped_lines.append(f"  {code}: '{acc.name}'")
            else:
                # Create new account
                # Determine account_type from code prefix (best effort)
                account_type = self._guess_account_type(code)
                new_acc = Account.create({
                    "code": code,
                    "name": name,
                    "account_type": account_type,
                    "company_id": Company.id,
                })
                created += 1
                code_map[code] = new_acc
                created_lines.append(f"  {code}: '{name}'")

        # Build detailed log
        log_parts = [
            f"Total filas: {len(rows)}",
            f"Creadas: {created} | Actualizadas: {updated} | Sin cambios: {skipped}",
            "",
        ]

        if created_lines:
            log_parts.append(f"=== CREADAS ({len(created_lines)}) ===")
            log_parts.extend(created_lines)
            log_parts.append("")

        if updated_lines:
            log_parts.append(f"=== ACTUALIZADAS ({len(updated_lines)}) ===")
            log_parts.extend(updated_lines)
            log_parts.append("")

        if skipped_lines:
            log_parts.append(f"=== SIN CAMBIOS ({len(skipped_lines)}) ===")
            log_parts.append("(Nombre en DB = Nombre en archivo)")
            log_parts.extend(skipped_lines)
            log_parts.append("")

        summary = "\n".join(log_parts)
        self.write({"log": summary})

        return {
            "type": "ir.actions.act_window",
            "res_model": "account.chart.replace.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _guess_account_type(self, code):
        """Best-guess account_type based on code prefix for Venezuelan CoA."""
        # Venezuelan CoA typical structure:
        # 1.x.x = Assets (asset_*)
        # 2.x.x = Liabilities (liability_*)
        # 3.x.x = Equity (equity_*)
        # 4.x.x = Income (income_*)
        # 5.x.x = Expense (expense_*)
        # 6.x.x = Expense (expense_*)
        # 7.x.x = Expense (expense_*)
        try:
            first_digit = code.split(".")[0]
        except (IndexError, AttributeError):
            return "expense"

        mapping = {
            "1": "asset_current",
            "2": "liability_current",
            "3": "equity",
            "4": "income",
            "5": "expense",
            "6": "expense",
            "7": "expense",
            "8": "expense",
        }
        return mapping.get(first_digit, "expense")
