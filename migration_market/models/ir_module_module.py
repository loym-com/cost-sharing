from odoo import fields, models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    migration_price_ids = fields.One2many(
        "migration.price",
        "module_id",
        string="Migration Prices",
    )