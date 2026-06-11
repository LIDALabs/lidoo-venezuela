from odoo import http


class AccountingReportsUsdController(http.Controller):

    @http.route("/web/download_sales_book_usd", type="http", auth="user")
    def download_sales_book_usd(self, **kw):
        sale_book_model = http.request.env["wizard.accounting.reports"]
        company_id = int(kw.get("company_id", 1))
        sale_book = sale_book_model.search([], order="id desc", limit=1)

        file = sale_book.with_context(usd_mode=True).generate_sales_book_usd(company_id)
        from_date = sale_book.date_from.strftime("%Y_%m_%d")
        to_date = sale_book.date_to.strftime("%Y_%m_%d")

        return http.request.make_response(
            file,
            headers=[
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                (
                    "Content-Disposition",
                    f"attachment;filename={from_date}-{to_date}-libro_de_venta_usd.xlsx",
                ),
            ],
        )

    @http.route("/web/download_purchase_book_usd", type="http", auth="user")
    def download_purchase_book_usd(self, **kw):
        purchase_book_model = http.request.env["wizard.accounting.reports"]
        company_id = int(kw.get("company_id", 1))
        purchase_book = purchase_book_model.search([], order="id desc", limit=1)

        file = purchase_book.with_context(usd_mode=True).generate_purchases_book_usd(company_id)
        from_date = purchase_book.date_from.strftime("%Y_%m_%d")
        to_date = purchase_book.date_to.strftime("%Y_%m_%d")

        return http.request.make_response(
            file,
            headers=[
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                (
                    "Content-Disposition",
                    f"attachment;filename={from_date}-{to_date}-libro_de_compra_usd.xlsx",
                ),
            ],
        )
