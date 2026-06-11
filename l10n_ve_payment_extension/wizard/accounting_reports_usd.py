import logging
from io import BytesIO

import xlsxwriter
from odoo import _, fields, models
from odoo.exceptions import UserError
from xlsxwriter import utility

_logger = logging.getLogger(__name__)
INIT_LINES = 8


class WizardAccountingReportsUsd(models.TransientModel):
    _inherit = "wizard.accounting.reports"

    # ------------------------------------------------------------
    # OVERRIDE: redirect to USD methods when usd_mode context is set
    # ------------------------------------------------------------
    def generate_report(self):
        if self.env.context.get("usd_mode"):
            if self.report == "sale":
                return self.download_sales_book_usd()
            return self.download_purchases_book_usd()
        return super().generate_report()

    # ------------------------------------------------------------
    # USD Excel generation
    # ------------------------------------------------------------
    def download_sales_book_usd(self):
        self.ensure_one()
        url = "/web/download_sales_book_usd?company_id=%s" % self.company_id.id
        return {"type": "ir.actions.act_url", "url": url, "target": "self"}

    def download_purchases_book_usd(self):
        self.ensure_one()
        url = "/web/download_purchase_book_usd?company_id=%s" % self.company_id.id
        return {"type": "ir.actions.act_url", "url": url, "target": "self"}

    def _get_foreign_currency(self):
        company = self.company_id or self.env.company
        foreign = company.currency_foreign_id
        if not foreign:
            raise UserError(_(
                "No foreign currency configured for the company. "
                "Please set a foreign currency in Accounting > Configuration > Settings."
            ))
        return company.currency_id, foreign

    MONETARY_FIELDS = [
        "total_sales_iva", "total_sales_not_iva",
        "total_purchases_iva", "total_purchases_not_iva",
        "amount_reduced_aliquot", "amount_general_aliquot", "amount_extend_aliquot",
        "tax_base_reduced_aliquot", "tax_base_general_aliquot", "tax_base_extend_aliquot",
        "amount_reduced_aliquot_no_deductible", "amount_general_aliquot_no_deductible",
        "amount_extend_aliquot_no_deductible",
        "tax_base_reduced_aliquot_no_deductible", "tax_base_general_aliquot_no_deductible",
        "tax_base_extend_aliquot_no_deductible",
        "iva_retained",
    ]

    def _get_bcv_rate(self, move):
        """Get the BCV rate for a specific move using the same logic as
        res.currency.rate.compute_rate (l10n_ve_rate).

        Uses the document's invoice_date (sale) or date (purchase) to look
        up the correct historical rate, NOT today's rate.
        """
        inv_date = move.invoice_date or move.date or fields.Date.today()
        foreign_currency = move.company_id.currency_foreign_id

        if not foreign_currency:
            _logger.warning("No foreign currency configured for company %s", move.company_id.name)
            return 0.0

        # Reuse compute_rate from l10n_ve_rate — same method used by payments.
        # It filters by company_id and returns inverse_company_rate for USD.
        Rate = self.env["res.currency.rate"]
        rate_values = Rate.compute_rate(foreign_currency.id, inv_date)

        if rate_values:
            bcv_rate = rate_values.get("foreign_rate", 0.0)
            _logger.info(
                "BCV rate for %s (date=%s): %s",
                move.name, inv_date, bcv_rate,
            )
            return bcv_rate

        return 0.0

    def _process_lines_usd(self, data_lines):
        """Procesa las líneas: busca la tasa BCV en res.currency.rate para
        la fecha de cada factura y convierte cada monto de VEF a USD."""
        for line in data_lines:
            move_id = line.get("_id")
            if not move_id:
                line["bcv_rate"] = 0.0
                continue

            move = self.env["account.move"].browse(move_id)
            bcv_rate = self._get_bcv_rate(move)

            if not bcv_rate:
                raise UserError(_(
                    "No exchange rate found for invoice %s (date: %s).\n"
                    "Please load the BCV rate for that date in Accounting > Configuration > Currencies."
                ) % (move.name or move_id, fields.Date.to_string(move.invoice_date or fields.Date.today())))

            line["bcv_rate"] = bcv_rate

            for key in self.MONETARY_FIELDS:
                if key in line and isinstance(line[key], (int, float)):
                    line[key] = line[key] / bcv_rate

        return data_lines

    def _usd_book_fields(self, base_fields):
        fields_copy = list(base_fields)
        insert_after = "document_date"
        for i, f in enumerate(fields_copy):
            if f.get("field") == insert_after:
                fields_copy.insert(i + 1, {
                    "name": "Tasa BCV",
                    "field": "bcv_rate",
                    "format": "number",
                    "size": 14,
                })
                break
        return fields_copy

    def _generate_usd_book_resume(self, worksheet, index_to_start, merge_format, cell_formats, data_lines):
        """Genera la sección de Resumen en USD usando tasa promedio del período."""
        is_purchase = self.report == "purchase"

        rates = [
            line["bcv_rate"] for line in data_lines
            if line.get("bcv_rate") and line["bcv_rate"] > 0
        ]
        avg_rate = sum(rates) / len(rates) if rates else 1.0

        header_idx = index_to_start + 2
        resume_headers = self.resume_book_headers()

        for idx, header in enumerate(resume_headers):
            nidx = idx * 2
            worksheet.merge_range(
                header_idx, nidx, header_idx, nidx + 1, header.get("name"), merge_format
            )
            worksheet.write(header_idx + 1, nidx, header.get("headers")[0])
            worksheet.write(header_idx + 1, nidx + 1, header.get("headers")[1])

        moves = self.search_moves()
        resume_columns = (
            self._resume_purchase_book_fields(moves)
            if is_purchase
            else self._resume_sale_book_fields(moves)
        )

        usd_resume_columns = []
        for resume in resume_columns:
            converted_values = []
            for val in resume.get("values", []):
                converted = val / avg_rate if (val and avg_rate) else 0.0
                converted_values.append(converted)
            usd_resume_columns.append({
                "name": resume["name"],
                "values": converted_values,
                "total": resume.get("total", False),
            })

        for idx, resume in enumerate(usd_resume_columns):
            row_resume = (index_to_start + 4) + idx
            worksheet.write(row_resume, 0, idx + 1)
            worksheet.write(row_resume, 1, resume.get("name"))

            total_line = 0
            for idx_line, line_val in enumerate(resume.get("values")):
                total_line = idx_line + 2
                worksheet.write(row_resume, idx_line + 2, line_val, cell_formats.get("number"))

            if resume.get("total"):
                for col_idx, col_letter in enumerate(["C", "D", "E", "F"]):
                    formula = f"=SUM({col_letter}{index_to_start + 5}:{col_letter}{row_resume})"
                    worksheet.write_formula(row_resume, 2 + col_idx, formula, cell_formats.get("number"))

            column_bi_range = (
                f"C{row_resume + 1}:{utility.xl_col_to_name(total_line - 1)}{row_resume + 1}"
            )
            column_df_range = (
                f"D{row_resume + 1}:{utility.xl_col_to_name(total_line)}{row_resume + 1}"
            )
            worksheet.write_formula(
                row_resume, total_line + 1,
                f"=SUMPRODUCT(--({column_bi_range}), --(MOD(COLUMN({column_bi_range}), 2)=1))",
                cell_formats.get("number"),
            )
            worksheet.write_formula(
                row_resume, total_line + 2,
                f"=SUMPRODUCT(--({column_df_range}), --(MOD(COLUMN({column_df_range}), 2)=0))",
                cell_formats.get("number"),
            )

    def _generate_usd_book(
        self, parse_method, book_title, company_id,
        fields_method_name="sale_book_fields"
    ):
        self.company_id = int(company_id) if isinstance(company_id, str) else company_id
        data_lines = getattr(self, parse_method)()
        data_lines = self._process_lines_usd(data_lines)

        file = BytesIO()
        workbook = xlsxwriter.Workbook(file, {"in_memory": True, "nan_inf_to_errors": True})
        worksheet = workbook.add_worksheet()

        cell_bold = workbook.add_format(
            {"bold": True, "center_across": True, "text_wrap": True, "bottom": True, "locked": True}
        )
        merge_format = workbook.add_format(
            {"bold": 1, "border": 1, "align": "center", "valign": "vcenter",
             "fg_color": "gray", "locked": True}
        )
        cell_formats = {
            "number": workbook.add_format({"num_format": "#,##0.00", "locked": True}),
            "percent": workbook.add_format({"num_format": "0.00%", "locked": True}),
        }

        worksheet.merge_range(
            "C1:M1",
            f"{self.company_id.name} - {self.company_id.l10n_ve_vat}",
            workbook.add_format({"bold": True, "center_across": True, "font_size": 18, "locked": True}),
        )
        worksheet.merge_range("C2:M2", f"Direccion:  {self.company_id.street}", cell_bold)
        worksheet.merge_range("C3:M3", book_title, cell_bold)
        worksheet.merge_range(
            "C4:M4",
            f"Desde {self._format_date(self.date_from)} Hasta {self._format_date(self.date_to)}",
            cell_bold,
        )

        base_fields = getattr(self, fields_method_name)()
        name_columns = self._usd_book_fields(base_fields)
        total_idx = 0

        for index, field in enumerate(name_columns):
            worksheet.set_column(index, index, len(field.get("name")) + 12)
            worksheet.merge_range(6, index, 7, index, field.get("name"), merge_format)

            for index_line, line in enumerate(data_lines):
                total_idx = (INIT_LINES + index_line) + 1
                val = line.get(field["field"])

                if field["field"] == "index":
                    worksheet.write(INIT_LINES + index_line, index, index_line + 1)
                elif field.get("format") == "number":
                    worksheet.write(
                        INIT_LINES + index_line, index,
                        float(val) if val is not None and val != "" else 0.0,
                        cell_formats.get("number"),
                    )
                elif field.get("format") == "percent":
                    worksheet.write(
                        INIT_LINES + index_line, index,
                        float(val) if val else 0.0,
                        cell_formats.get("percent"),
                    )
                else:
                    worksheet.write(INIT_LINES + index_line, index, val if val is not None else "")

            if field.get("format") == "number" and field["field"] != "bcv_rate":
                col = utility.xl_col_to_name(index)
                worksheet.write_formula(
                    total_idx, index,
                    f"=SUM({col}9:{col}{total_idx})", cell_formats.get("number"),
                )

        self._generate_usd_book_resume(worksheet, total_idx, merge_format, cell_formats, data_lines)

        worksheet.protect(password="secure")
        workbook.close()
        return file.getvalue()

    def generate_sales_book_usd(self, company_id):
        return self._generate_usd_book(
            parse_method="parse_sale_book_data",
            book_title="Libro de Ventas $",
            company_id=company_id,
            fields_method_name="sale_book_fields",
        )

    def generate_purchases_book_usd(self, company_id):
        return self._generate_usd_book(
            parse_method="parse_purchase_book_data",
            book_title="Libro de Compras $",
            company_id=company_id,
            fields_method_name="purchase_book_fields",
        )
