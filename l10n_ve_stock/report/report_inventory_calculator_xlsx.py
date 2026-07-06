from odoo import models
from odoo.tools import format_amount


class ReportInventoryCalculatorXlsx(models.AbstractModel):
    _name = "report.l10n_ve_stock.report_inventory_calculator_xlsx"
    _description = "Reporte XLSX de Calculadora de Inventario"
    _inherit = "report.report_xlsx.abstract"

    def _get_report_values(self, docids, data=None):
        docs = self.env["inventory.calculator"].browse(docids)
        return {
            "xlsx": True,
            "docs": docs,
        }

    def generate_xlsx_report(self, workbook, data, docs):
        # Formatos
        header_fmt = workbook.add_format({
            "bold": True,
            "bg_color": "#4472C4",
            "font_color": "#FFFFFF",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        })
        subheader_fmt = workbook.add_format({
            "bold": True,
            "bg_color": "#D9E2F3",
            "border": 1,
            "align": "left",
        })
        money_fmt = workbook.add_format({
            "num_format": "#,##0.00",
            "border": 1,
        })
        money_bold_fmt = workbook.add_format({
            "num_format": "#,##0.00",
            "border": 1,
            "bold": True,
        })
        cell_fmt = workbook.add_format({"border": 1})
        bold_fmt = workbook.add_format({"bold": True, "border": 1})

        for doc in docs:
            sheet_name = doc.name or "Calculadora"
            sheet = workbook.add_worksheet(sheet_name[:31])
            col = 0
            row = 0

            # -- Seccion 1: Informacion General --
            sheet.write(row, 0, "Calculadora de Inventario", header_fmt)
            sheet.merge_range(row, 0, row, 3,
                             "Calculadora de Inventario", header_fmt)
            row += 1

            info_data = [
                ("Referencia", doc.name),
                ("Fecha", str(doc.date) if doc.date else ""),
                ("Estado", doc.state),
                ("Empresa", doc.company_id.name),
                ("Responsable", doc.user_id.name),
                ("Ubicacion Destino", doc.location_dest_id.display_name or ""),
                ("Ubicacion Virtual", doc.virtual_location_id.display_name or ""),
            ]
            for label, value in info_data:
                sheet.write(row, 0, label, bold_fmt)
                sheet.write(row, 1, value or "", cell_fmt)
                sheet.merge_range(row, 1, row, 3, value or "", cell_fmt)
                row += 1

            row += 1

            # -- Seccion 2: Productos Finales --
            sheet.write(row, 0, "Productos Finales", subheader_fmt)
            sheet.merge_range(row, 0, row, 3,
                             "Productos Finales", subheader_fmt)
            row += 1

            finished_headers = [
                "Producto", "Cantidad", "Costo Unit. MP", "Costo Total MP",
            ]
            for c, h in enumerate(finished_headers):
                sheet.write(row, c, h, header_fmt)
            row += 1

            for line in doc.finished_product_ids:
                sheet.write(row, 0, line.product_id.display_name or "",
                            cell_fmt)
                sheet.write_number(row, 1, line.quantity, cell_fmt)
                sheet.write_number(row, 2, line.raw_cost_per_unit, money_fmt)
                sheet.write_number(row, 3, line.raw_cost_total, money_fmt)
                row += 1

            row += 1

            # -- Seccion 3: Materias Primas --
            sheet.write(row, 0, "Materias Primas", subheader_fmt)
            sheet.merge_range(row, 0, row, 3,
                             "Materias Primas", subheader_fmt)
            row += 1

            raw_headers = [
                "Materia Prima", "Cantidad", "Costo Unitario", "Costo Total",
            ]
            for c, h in enumerate(raw_headers):
                sheet.write(row, c, h, header_fmt)
            row += 1

            total_raw_cost = 0.0
            for raw in doc.raw_material_ids:
                cost_unit = raw.product_id.standard_price or 0.0
                cost_total = cost_unit * raw.quantity
                total_raw_cost += cost_total
                sheet.write(row, 0, raw.product_id.display_name or "",
                            cell_fmt)
                sheet.write_number(row, 1, raw.quantity, cell_fmt)
                sheet.write_number(row, 2, cost_unit, money_fmt)
                sheet.write_number(row, 3, cost_total, money_fmt)
                row += 1

            row += 1

            # -- Seccion 4: Resumen de Costos --
            sheet.write(row, 0, "Resumen de Costos", subheader_fmt)
            sheet.merge_range(row, 0, row, 3,
                             "Resumen de Costos", subheader_fmt)
            row += 1

            sheet.write(row, 0, "Total Materias Primas", bold_fmt)
            sheet.write_number(row, 1, doc.total_raw_cost, money_bold_fmt)
            row += 1

            sheet.write(row, 0, "Productos Finales", bold_fmt)
            sheet.write_number(row, 1, len(doc.finished_product_ids), cell_fmt)
            row += 1

            sheet.write(row, 0, "Materias Primas", bold_fmt)
            sheet.write_number(row, 1, len(doc.raw_material_ids), cell_fmt)
            row += 1

            # Ajustar anchos de columna
            sheet.set_column(0, 0, 35)
            sheet.set_column(1, 1, 15)
            sheet.set_column(2, 2, 18)
            sheet.set_column(3, 3, 18)
