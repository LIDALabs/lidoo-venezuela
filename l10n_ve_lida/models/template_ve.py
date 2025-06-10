# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    @template("ve_lida")
    def _get_ve_lida_template_data(self):
        return {
            "code_digits": "12",
            "property_account_receivable_id": "acc_cuentas_por_cobrar_clientes",
            "property_account_payable_id": "acc_cuentas_por_pagar",
            "property_account_expense_categ_id": "acc_otros_egresos_no_atribuibles",
            "property_account_income_categ_id": "acc_ingreso_principal",
            "name": _("LIDA/Venezuela"),
        }

    @template("ve_lida", "res.company")
    def _get_ve_lida_res_company(self):
        return {
            self.env.company.id: {
                "currency_id": "base.VEF",
                "account_fiscal_country_id": "base.ve",
                "bank_account_code_prefix": "1.1.1.11.",
                "cash_account_code_prefix": "1.1.1.01.",
                "transfer_account_code_prefix": "1.1.1.50.",
                "account_default_pos_receivable_account_id": "acc_cuentas_por_cobrar_clientes",
                "income_currency_exchange_account_id": "acc_otros_ingresos",
                "expense_currency_exchange_account_id": "acc_otros_egresos_no_atribuibles",
                "deferred_expense_account_id": "acc_anticipo_dado_a_proveedores",
                "deferred_revenue_account_id": "acc_anticipo_recibido_de_clientes",
                "transfer_account_id": "acc_transferencias_internas",
                "account_journal_suspense_account_id": "acc_transito_bancario",
                "account_sale_tax_id": "IVA_16_SALE",
                "account_purchase_tax_id": "IVA_16_PURCHASE",
            },
        }

    @template('ve_lida', 'account.journal')
    def _get_ve_lida_account_journal(self):
        """ In case of a Venezuelan CoA, we modify the default values of the sales journal to be a preprinted journal"""
        return {
            "sale": {
                "name": "Facturas de ventas",
                "invoice_reference_type": "invoice",
                "type": "sale",
                "code": "FV00",
                "default_account_id": "acc_ingresos_por_ventas",
            },

            "lida_delivery_notes": {
                "name": "Ordenes de entrega",
                "invoice_reference_type": "invoice",
                "type": "sale",
                "code": "OE",
                "default_account_id": "acc_ingresos_por_ventas",
            },

            "purchase": {
                "name": "Facturas de proveedores",
                "invoice_reference_type": "invoice",
                "type": "purchase",
                "code": "FP",
                "default_account_id": "acc_compras",
            },

            "lida_supplier_receipts": {
                "name": "Recibos de proveedores",
                "invoice_reference_type": "invoice",
                "type": "purchase",
                "code": "RP",
                "default_account_id": "acc_compras",
            },

            "bank": {
                "name": "Banco",
                "invoice_reference_type": "invoice",
                "type": "bank",
                "code": "Bank",
                "outbound_payment_method_line_ids": [
                    (0, 0, {
                        'name': 'Pago saliente - Banco',
                        'payment_method_id': 'account.account_payment_method_manual_out',
                        'payment_account_id': 'acc_banco_generico',
                    })],
                "default_account_id": "acc_banco_generico",
            },

            "cash": {
                "name": "Efectivo Bs",
                "invoice_reference_type": "invoice",
                "type": "cash",
                "code": "EBs",
                "outbound_payment_method_line_ids": [
                    (0, 0, {
                        'name': 'Pago saliente - Efectivo Bs',
                        'payment_method_id': 'account.account_payment_method_manual_out',
                        'payment_account_id': 'acc_caja_principal_nacional',
                    })],
                "default_account_id": "acc_caja_principal_nacional",
            },

            "lida_cash_usd": {
                "name": "Efectivo $",
                "invoice_reference_type": "invoice",
                "type": "cash",
                "code": "EDiv",
                "outbound_payment_method_line_ids": [
                    (0, 0, {
                        'name': 'Pago saliente - Efectivo $',
                        'payment_method_id': 'account.account_payment_method_manual_out',
                        'payment_account_id': 'acc_caja_dolares',
                    })],
                "default_account_id": "acc_caja_dolares",
            },

            "lida_inventory_valuation": {
                "name": "Valorización de inventario",
                "invoice_reference_type": "invoice",
                "type": "general",
                "code": "VI",
            },

            "general": {
                "name": "Operaciones varias",
                "invoice_reference_type": "invoice",
                "type": "general",
                "code": "OP",
            },

            "lida_opening_balances": {
                "name": "Saldos Iniciales",
                "invoice_reference_type": "invoice",
                "type": "general",
                "code": "SI",
            },
        }

    def _get_accounts_data_values(self, company, template_data):
        accounts_data = super()._get_accounts_data_values(company, template_data)
        if company.account_fiscal_country_id.code == 'VE':
            accounts_data.update({
                # 'account_journal_suspense_account_id': {
                #     'name': _("Bank Suspense Account"),
                #     'code': '1.1.1.50.990',
                #     'account_type': 'asset_current',
                # },
                'account_journal_payment_debit_account_id': {
                    'name': _("Outstanding Receipts"),
                    'code': "1.1.1.50.991",
                    'account_type': 'asset_current',
                    'reconcile': True,
                },
                'account_journal_payment_credit_account_id': {
                    'name': _("Outstanding Payments"),
                    'code': "1.1.1.50.992",
                    'account_type': 'asset_current',
                    'reconcile': True,
                },
                'account_journal_early_pay_discount_loss_account_id': {
                    'name': _("Cash Discount Loss"),
                    'code': '7.1.0.00.991',
                    'account_type': 'expense',
                },
                'account_journal_early_pay_discount_gain_account_id': {
                    'name': _("Cash Discount Gain"),
                    'code': '4.2.0.00.991',
                    'account_type': 'income_other',
                },
                'default_cash_difference_income_account_id': {
                    'name': _("Cash Difference Gain"),
                    'code': '4.2.0.00.992',
                    'account_type': 'income_other',
                    'tag_ids': [(6, 0, self.ref('account.account_tag_investing').ids)],
                },
                'default_cash_difference_expense_account_id': {
                    'name': _("Cash Difference Loss"),
                    'code': "7.1.0.00.992",
                    'account_type': 'expense',
                    'tag_ids': [(6, 0, self.ref('account.account_tag_investing').ids)],
                },
            })

            del accounts_data['account_journal_suspense_account_id']
            del accounts_data['transfer_account_id']
        return accounts_data
