from odoo import fields, models


class MigrationPledge(models.Model):
    _name = "migration.market.pledge"
    _description = "Migration Market Pledge"
    _order = "partner_id, id"

    partner_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="cascade",
        string="Customer",
    )
    module_ids = fields.Many2many(
        "ir.module.module",
        string="Modules",
        required=True,
    )
    wtp = fields.Monetary(
        string="Willingness to Pay",
        required=True,
        currency_field="currency_id",
    )
    value_of_quality = fields.Float(string="Value of Quality", default=0.0)
    minimum_score = fields.Float(string="Minimum Score", required=True, default=0.0)
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    active = fields.Boolean(default=True)