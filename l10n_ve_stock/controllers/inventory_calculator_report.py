import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    _logger.warning("xlsxwriter not installed. XLSX export will not work.")
    xlsxwriter = None


class InventoryCalculatorReportController(http.Controller):

    @http.route(
        "/web/inventory_calculator_xlsx",
        type="http",
        auth="user",
        methods=["GET"],
    )
    def download_inventory_calculator_xlsx(self, calculator_id=None, **kw):
        if not xlsxwriter:
            return request.make_response(
                "xlsxwriter library is not installed.",
                headers=[("Content-Type", "text/plain")],
                status=500,
            )

        if not calculator_id:
            return request.make_response(
                "Missing calculator_id parameter.",
                headers=[("Content-Type", "text/plain")],
                status=400,
            )

        calculator = request.env["inventory.calculator"].browse(int(calculator_id))
        if not calculator.exists():
            return request.make_response(
                "Calculator not found.",
                headers=[("Content-Type", "text/plain")],
                status=404,
            )

        xlsx_file = calculator._generate_xlsx_report()

        return request.make_response(
            xlsx_file,
            headers=[
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                (
                    "Content-Disposition",
                    "attachment;filename=Calculadora_%s.xlsx" % (calculator.name or ""),
                ),
            ],
        )
