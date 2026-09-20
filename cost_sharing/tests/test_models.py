from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestCostSharingModels(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["res.partner"]
        cls.rate_model = cls.env["res.partner.rate"]
        cls.client_model = cls.env["cs.client"]
        cls.partner_a = cls.partner_model.create({"name": "Partner A"})
        cls.partner_b = cls.partner_model.create({"name": "Partner B"})
        cls.partner_c = cls.partner_model.create({"name": "Partner C"})

    def test_rating_defaults_to_one_and_rejects_low_outgoing_average(self):
        rating = self.rate_model.create(
            {
                "from_partner_id": self.partner_a.id,
                "to_partner_id": self.partner_b.id,
            }
        )
        self.assertEqual(rating.rate, "1")
        with self.assertRaises(ValidationError):
            self.rate_model.create(
                {
                    "from_partner_id": self.partner_a.id,
                    "to_partner_id": self.partner_c.id,
                    "rate": "0",
                }
            )

    def test_down_rating_is_allowed_when_outgoing_average_stays_at_least_one(self):
        self.rate_model.create(
            {
                "from_partner_id": self.partner_a.id,
                "to_partner_id": self.partner_b.id,
                "rate": "3",
            }
        )
        rating = self.rate_model.create(
            {
                "from_partner_id": self.partner_a.id,
                "to_partner_id": self.partner_c.id,
                "rate": "0",
            }
        )
        self.assertEqual(rating.rate, "0")

    def test_client_gets_unique_uuid(self):
        client = self.client_model.create({"partner_id": self.partner_a.id})
        self.assertTrue(client.uuid)
        self.assertEqual(len(client.uuid), 36)
        self.assertIn("Partner A", client.name)
