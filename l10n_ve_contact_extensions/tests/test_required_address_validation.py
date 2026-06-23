from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestRequiredAddressValidation(TransactionCase):
    def test_non_address_write_does_not_require_complete_address(self):
        partner = self.env.company.partner_id

        partner.write({"country_id": self.env.ref("base.ve").id})
