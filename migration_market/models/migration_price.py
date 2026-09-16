from odoo import fields, models


class MigrationPrice(models.Model):
    _name = "migration.price"
    _description = "Migration Module Price"
    _order = "supplier_id, module_id"
    _rec_name = "module_id"

    supplier_id = fields.Many2one(
        "res.partner",
        required=True,
        ondelete="cascade",
        domain=[("is_migration_supplier", "=", True)],
    )
    module_id = fields.Many2one(
        "ir.module.module",
        required=True,
        ondelete="cascade",
    )
    price = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one(
        related="supplier_id.migration_currency_id",
        readonly=True,
    )
    supplier_score = fields.Float(
        related="supplier_id.migration_supplier_score",
        readonly=True,
    )
    supplier_capacity = fields.Monetary(
        related="supplier_id.migration_supplier_capacity",
        currency_field="currency_id",
        readonly=True,
    )

    _supplier_module_unique = models.Constraint(
        "UNIQUE(supplier_id, module_id)",
        "A supplier can only have one price per module.",
    )