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
                "inbound_payment_method_line_ids": [
                    (0, 0, {
                        'name': 'Pago en efectivo',
                        'payment_method_id': 'account.account_payment_method_manual_in',
                        'payment_account_id': 'acc_caja_principal_nacional',
                    })],
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
                "currency_id": "base.USD",
                "inbound_payment_method_line_ids": [
                    (0, 0, {
                        'name': 'Pago en efectivo',
                        'payment_method_id': 'account.account_payment_method_manual_in',
                        'payment_account_id': 'acc_caja_dolares',
                    })],
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

            "lida_withholding_iva_customers": {
                "name": "Retenciones IVA clientes",
                "type": "cash",
                "code": "RIVA",
                "inbound_payment_method_line_ids": [
                    (0, 0, {
                        'name': 'Retención de IVA',
                        'payment_method_id': 'account.account_payment_method_manual_in',
                        'payment_account_id': 'acc_retencion_iva',
                    })],
                "outbound_payment_method_line_ids": [fields.Command.clear()],
                "default_account_id": "acc_retencion_iva",
            },

            "lida_withholding_islr_customers": {
                "name": "Retenciones ISLR clientes",
                "type": "cash",
                "code": "RISLR",
                "inbound_payment_method_line_ids": [
                    (0, 0, {
                        'name': 'Retención de ISLR',
                        'payment_method_id': 'account.account_payment_method_manual_in',
                        'payment_account_id': 'acc_retencion_de_islr',
                    })],
                "outbound_payment_method_line_ids": [fields.Command.clear()],
                "default_account_id": "acc_retencion_de_islr",
            },

            "lida_withholding_iva_suppliers": {
                "name": "Retenciones IVA proveedores",
                "type": "cash",
                "code": "RPIVA",
                "inbound_payment_method_line_ids": [fields.Command.clear()],
                "outbound_payment_method_line_ids": [
                    (0, 0, {
                        'name': 'Retención de IVA',
                        'payment_method_id': 'account.account_payment_method_manual_out',
                        'payment_account_id': 'acc_iva_retenido_por_pagar',
                    })],
                "default_account_id": "acc_iva_retenido_por_pagar",
            },

            "lida_withholding_islr_suppliers": {
                "name": "Retenciones ISLR proveedores",
                "type": "cash",
                "code": "RPSLR",
                "inbound_payment_method_line_ids": [fields.Command.clear()],
                "outbound_payment_method_line_ids": [
                    (0, 0, {
                        'name': 'Retención de ISLR',
                        'payment_method_id': 'account.account_payment_method_manual_out',
                        'payment_account_id': 'acc_retenciones_de_islr_por_pagar',
                    })],
                "default_account_id": "acc_retenciones_de_islr_por_pagar",
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

    def _post_load_data(self, template_code, company, template_data):
        """ Loads the default accounts into the settings."""
        super()._post_load_data(template_code, company, template_data)
        if template_code == 've_lida':
            # Base settings
            if 'currency_foreign_id' in company._fields and not company.currency_foreign_id:
                company.currency_foreign_id = self.ref('base.USD', raise_if_not_found=False)
            if 'tax_period' in company._fields and not company.tax_period:
                company.tax_period = "monthly"

            # Taxes
            if 'exent_aliquot_sale' in company._fields:
                company.exent_aliquot_sale = company.exent_aliquot_sale or self.ref('EXEMPT_SALE', raise_if_not_found=False)
            if 'general_aliquot_sale' in company._fields:
                company.general_aliquot_sale = company.general_aliquot_sale or self.ref('IVA_16_SALE', raise_if_not_found=False)
            if 'reduced_aliquot_sale' in company._fields:
                company.reduced_aliquot_sale = company.reduced_aliquot_sale or self.ref('IVA_8_SALE', raise_if_not_found=False)
            if 'extend_aliquot_sale' in company._fields:
                company.extend_aliquot_sale = company.extend_aliquot_sale or self.ref('IVA_31_SALE', raise_if_not_found=False)

            if 'exent_aliquot_purchase' in company._fields:
                company.exent_aliquot_purchase = company.exent_aliquot_purchase or self.ref('EXEMPT_PURCHASE', raise_if_not_found=False)
            if 'general_aliquot_purchase' in company._fields:
                company.general_aliquot_purchase = company.general_aliquot_purchase or self.ref('IVA_16_PURCHASE', raise_if_not_found=False)
            if 'reduced_aliquot_purchase' in company._fields:
                company.reduced_aliquot_purchase = company.reduced_aliquot_purchase or self.ref('IVA_8_PURCHASE', raise_if_not_found=False)
            if 'extend_aliquot_purchase' in company._fields:
                company.extend_aliquot_purchase = company.extend_aliquot_purchase or self.ref('IVA_31_PURCHASE', raise_if_not_found=False)

            # Invoices
            Journals = self.env["account.journal"]
            if 'series_correlative_sequence_id' in Journals._fields:
                correlative_sequence = self.ref('l10n_ve_invoice.invoice_correlative', raise_if_not_found=False)
                if correlative_sequence:
                    sale_journals = Journals.search([('company_id', '=', company.id), ('type', '=', 'sale'), ('series_correlative_sequence_id', '=', False)])
                    if sale_journals:
                        sale_journals.write({'series_correlative_sequence_id': correlative_sequence.id})

            # IGTF
            if 'customer_account_igtf_id' in company._fields:
                company.customer_account_igtf_id = company.customer_account_igtf_id or self.ref('acc_igtf_por_pagar', raise_if_not_found=False)
            if 'supplier_account_igtf_id' in company._fields:
                company.supplier_account_igtf_id = company.supplier_account_igtf_id or self.ref('acc_otros_egresos_no_atribuibles', raise_if_not_found=False)
            if 'is_igtf' in Journals._fields:
                bs_currency = self.ref('base.VEF', raise_if_not_found=False)
                igtf_journals = Journals.search([('company_id', '=', company.id), ('type', 'in', ['cash', 'bank']), ('currency_id', '!=', bs_currency.id)])
                if igtf_journals:
                    igtf_journals.write({'is_igtf': True})

                # Retenciones
            if 'iva_supplier_retention_journal_id' in company._fields:
                company.iva_supplier_retention_journal_id = company.iva_supplier_retention_journal_id or self.ref('lida_withholding_iva_suppliers', raise_if_not_found=False)
            if 'iva_customer_retention_journal_id' in company._fields:
                company.iva_customer_retention_journal_id = company.iva_customer_retention_journal_id or self.ref('lida_withholding_iva_customers', raise_if_not_found=False)
            if 'islr_supplier_retention_journal_id' in company._fields:
                company.islr_supplier_retention_journal_id = company.islr_supplier_retention_journal_id or self.ref('lida_withholding_islr_suppliers', raise_if_not_found=False)
            if 'islr_customer_retention_journal_id' in company._fields:
                company.islr_customer_retention_journal_id = company.islr_customer_retention_journal_id or self.ref('lida_withholding_islr_customers', raise_if_not_found=False)
