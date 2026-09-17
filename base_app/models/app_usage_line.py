import odoo
from odoo import api, fields, models
from datetime import date
from collections import defaultdict


class AppUsageLine(models.Model):
    _name = "app.usage.line"
    _description = "Daily App Usage Log"
    _order = "date desc, module_version_id"

    module_version_id = fields.Many2one(
        "app.module.version",
        string="App",
        required=True,
        ondelete="cascade",
    )

    # contract_id = fields.Many2one(
    #     "contract.contract",
    #     string="Contract",
    #     required=False,
    #     help="Contract under which this app is used.",
    # )

    date = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
    )

    active_users = fields.Integer(
        string="Active Users",
        help="Number of active users for this module and date.",
    )

    # _sql_constraints = [
    #     (
    #         "unique_module_date",
    #         "unique(module_version_id, date, contract_id)",
    #         "Each module + contract can have only one daily usage log per date.",
    #     )
    # ]

    # -------------------------------------------------------------
    # Daily cron
    # -------------------------------------------------------------
    @api.model
    def cron_log_daily_usage(self, version=None):
        """Create app.usage.line entries for installed apps per contract."""
        # Exit if lines already exist
        today = fields.Date.today()
        lines = self.search([("date", "=", today)])
        if lines:
            return

        version = version or odoo.release.version
        modules = self.env["ir.module.module"].search([("state", "=", "installed")])
        if not modules:
            return
        
        AppVersions = self.env["app.module.version"]
        AppVersions.create_missing_versions()
        module_versions = AppVersions.search([("version", "=", version)]) 

        group_ids = module_versions.mapped("user_group_id.id")
        if not group_ids:
            return

        # Count active (non-portal, non-inactive) users per group
        self.env.cr.execute("""
            SELECT gu.gid AS group_id, COUNT(u.id) AS user_count
            FROM res_groups_users_rel gu
            JOIN res_users u ON u.id = gu.uid
            WHERE gu.gid = ANY(%s)
              AND u.active = TRUE
              AND u.share = FALSE
            GROUP BY gu.gid
        """, (group_ids,))

        user_counts = dict(self.env.cr.fetchall())
        lines_to_create = []

        # 🧩 Extend here if you later want to link contracts dynamically.
        # For now, contract_id = False unless you have logic to attach it.
        for module_version in module_versions:
            count = user_counts.get(module_version.user_group_id.id, 0)
            lines_to_create.append({
                "module_version_id": module_version.id,
                # "contract_id": False,
                "date": today,
                "active_users": count,
            })

        if lines_to_create:
            self.create(lines_to_create)
