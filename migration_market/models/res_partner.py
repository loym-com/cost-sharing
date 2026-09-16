from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_migration_supplier = fields.Boolean(string="Migration Supplier")
    migration_supplier_score = fields.Float(string="Migration Score")
    migration_supplier_capacity = fields.Monetary(
        string="Migration Capacity",
        currency_field="migration_currency_id",
    )
    migration_currency_id = fields.Many2one(
        "res.currency",
        string="Migration Currency",
        default=lambda self: self.env.company.currency_id,
    )
    migration_price_ids = fields.One2many(
        "migration.price",
        "supplier_id",
        string="Migration Prices",
    )
    migration_pledge_ids = fields.One2many(
        "migration.market.pledge",
        "partner_id",
        string="Migration Pledges",
    )
