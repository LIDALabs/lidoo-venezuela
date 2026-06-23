from odoo import fields, models


class InvoicePresetNote(models.Model):
    _name = "invoice.preset.note"
    _description = "Invoice Preset Note"
    _order = "name"

    name = fields.Char(string="Name", required=True, translate=True)
    text = fields.Text(string="Text", required=True, translate=True)
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        company_dependent=True,
    )
