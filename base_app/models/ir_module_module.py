from datetime import date

from odoo import api, fields, models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    module_version_ids = fields.One2many(
        "app.module.version",
        "module_id",
    )



    def _compute_cost_mig_to_next_version(self):
        for record in self:
            record.cost_mig_to_next_version = record.minutes_mig_to_next_version * 20

    def _compute_current_price(self):
        users_count = self.env["res.users"].search_count([("share", "=", False)])
        for record in self:
            # 20 nok/min = 1200 nok/hour
            record.current_price = record.minutes_worked * 20 / 100 * sqrt(users_count)



    # Temporary, read from csv
    minutes_worked = fields.Integer(
        string="Minutes worked",
        related="module_version_ids.minutes_worked",
    )
    year_price = fields.Monetary(
        string="Price: minutes*20/100*sqrt(users)",
        related="module_version_ids.current_price",
        help="Latest valid price per user from the App Price List."
    )
    minutes_mig_to_next_version = fields.Integer(
        string="Migration Work (estimated minutes)",
        related="module_version_ids.minutes_mig_to_next_version",
    )
    cost_mig_to_next_version = fields.Monetary(
        string="Cost to migrate",
        related="module_version_ids.cost_mig_to_next_version",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        related="module_version_ids.currency_id",
    )
