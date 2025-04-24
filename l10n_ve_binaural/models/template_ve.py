# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("ve_binaural")
    def _get_ve_binaural_template_data(self):
        return {
            "code_digits": "7",
            "property_account_receivable_id": "account_activa_account_10104001",
            "property_account_payable_id": "account_activa_account_20101004",
            "property_account_expense_categ_id": "account_activa_account_60301027",
            "property_account_income_categ_id": "account_activa_account_501",
            "name": _("Binaural/Venezuela"),
        }

    @template("ve_binaural", "res.company")
    def _get_ve_binaural_res_company(self):
        return {
            self.env.company.id: {
                "currency_id": "base.VEF",
                "account_fiscal_country_id": "base.ve",
                "bank_account_code_prefix": "1113",
                "cash_account_code_prefix": "1111",
                "transfer_account_code_prefix": "1129003",
                "account_default_pos_receivable_account_id": "account_activa_account_10102",
                "income_currency_exchange_account_id": "account_activa_account_30201002",
                "expense_currency_exchange_account_id": "account_activa_account_40301001",
                "account_sale_tax_id": "IVA_16_SALE",
                "account_purchase_tax_id": "IVA_16_PURCHASE",
            },
        }

    @template('ve_binaural', 'account.journal')
    def _get_ve_binaural_account_journal(self):
        """ In case of a Venezuelan CoA, we modify the default values of the sales journal to be a preprinted journal"""
        return {
            "sale": {
                "name": "Facturas de ventas",
                "invoice_reference_type": "invoice",
                "type": "sale",
                # <field name="invoice_reference_model">odoo</field>
                "code": "FV00",
                # <field name="company_id" ref="base.main_company"/>
                "default_account_id": "account_activa_account_40101001",
            },

            "binaural_account_journal_delivery_notes": {
                "name": "Notas de entrega",
                "invoice_reference_type": "invoice",
                "type": "sale",
                # <field name="invoice_reference_model">odoo</field>
                "code": "NE",
                "default_account_id": "account_activa_account_40101001",
            },

            "purchase": {
                "name": "Facturas de proveedores",
                "invoice_reference_type": "invoice",
                "type": "purchase",
                # <field name="invoice_reference_model">odoo</field>
                "code": "FP",
                # <field name="company_id" ref="base.main_company"/>
                "default_account_id": "account_activa_account_60101001",
            },

            "binaural_account_journal_supplier_receipts": {
                "name": "Recibos de proveedores",
                "invoice_reference_type": "invoice",
                "type": "purchase",
                # <field name="invoice_reference_model">odoo</field>
                "code": "RP",
                # <field name="company_id" ref="base.main_company"/>
                "default_account_id": "account_activa_account_60101001",
            },

            "bank": {
                "name": "Banco",
                "invoice_reference_type": "invoice",
                "type": "bank",
                # <field name="invoice_reference_model">odoo</field>
                "code": "Bank",
                # <field name="company_id" ref="base.main_company"/>
                "outbound_payment_method_line_ids": [
                    (0, 0, {
                        'name': 'Pago saliente - Banco',
                        'payment_method_id': 'account.account_payment_method_manual_out',
                        'payment_account_id': 'account_activa_account_10102001',
                    })],
                "default_account_id": "account_activa_account_10102001",
            },

            "cash": {
                "name": "Efectivo Bs",
                "invoice_reference_type": "invoice",
                "type": "cash",
                # <field name="invoice_reference_model">odoo</field>
                "code": "EBs",
                # <field name="company_id" ref="base.main_company"/>
                "outbound_payment_method_line_ids": [
                    (0, 0, {
                        'name': 'Pago saliente - Efectivo Bs',
                        'payment_method_id': 'account.account_payment_method_manual_out',
                        'payment_account_id': 'account_activa_account_10101001',
                    })],
                "default_account_id": "account_activa_account_10101001",
            },

            "binaural_account_journal_cash_usd": {
                "name": "Efectivo $",
                "invoice_reference_type": "invoice",
                "type": "cash",
                # <field name="invoice_reference_model">odoo</field>
                "code": "EDiv",
                # <field name="company_id" ref="base.main_company"/>
                "outbound_payment_method_line_ids": [
                    (0, 0, {
                        'name': 'Pago saliente - Efectivo $',
                        'payment_method_id': 'account.account_payment_method_manual_out',
                        'payment_account_id': 'account_activa_account_10101003',
                    })],
                "default_account_id": "account_activa_account_10101003",
            },

            "binaural_account_journal_inventory_valuation": {
                "name": "Valorización de inventario",
                "invoice_reference_type": "invoice",
                "type": "general",
                # <field name="invoice_reference_model">odoo</field>
                "code": "VI",
                # <field name="company_id" ref="base.main_company"/>
            },

            "general": {
                "name": "Operaciones varias",
                "invoice_reference_type": "invoice",
                "type": "general",
                # <field name="invoice_reference_model">odoo</field>
                "code": "OP",
                # <field name="company_id" ref="base.main_company"/>
            },

            "binaural_account_journal_opening_balances": {
                "name": "Saldos Iniciales",
                "invoice_reference_type": "invoice",
                "type": "general",
                # <field name="invoice_reference_model">odoo</field>
                "code": "SI",
                # <field name="company_id" ref="base.main_company"/>
            },
        }
