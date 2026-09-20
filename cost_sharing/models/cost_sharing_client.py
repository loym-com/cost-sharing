import uuid

from odoo import api, fields, models


class CostSharingClient(models.Model):
    _name = "cs.client"
    _description = "Cost Sharing Client"
    _rec_name = "name"

    name = fields.Char(compute="_compute_name", store=True)
    partner_id = fields.Many2one("res.partner", required=True, ondelete="restrict")
    uuid = fields.Char(default=lambda self: str(uuid.uuid4()), required=True, copy=False, index=True)
    number_of_internal_users = fields.Integer()
    demand_ids = fields.One2many("cs.client.demand", "client_id", string="Demands")

    _sql_constraints = [
        ("unique_uuid", "unique(uuid)", "The client UUID must be unique."),
    ]

    @api.depends("partner_id", "uuid")
    def _compute_name(self):
        for client in self:
            client.name = "%s (%s)" % (client.partner_id.display_name, client.uuid)


class CostSharingClientDemand(models.Model):
    _name = "cs.client.demand"
    _description = "Cost Sharing Client Demand"

    client_id = fields.Many2one("cs.client", required=True, ondelete="cascade")
    attribute_value_id = fields.Many2one(
        "product.attribute.value",
        required=True,
        # domain="[('attribute_id', '=', ref('cost_sharing.product_attribute_migration'))]",
    )
    willing_to_pay = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(related="client_id.partner_id.cs_currency_id", readonly=True)
    app_ids = fields.Many2many("ir.module.module", string="Apps")
