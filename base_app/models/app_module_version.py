import csv
import os

from datetime import date
from math import sqrt

import odoo
from odoo import api, fields, models
from odoo.release import version_info


class AppModuleVersion(models.Model):
    _name = "app.module.version"
    _description = "app.module.version"
    _order = "module_name"
    _sql_constraints = [
        (
            "unique_module_version",
            "unique(module_id, version)",
            "Each module can only have one record per version!",
        )
    ]

    def _compute_cost_mig_to_next_version(self):
        for record in self:
            record.cost_mig_to_next_version = record.minutes_mig_to_next_version * 2

    def __compute_current_price(self):
        PriceList = self.env["app.pricelist"]
        today = date.today()
        for module in self:
            price_record = PriceList.search([
                ("module_version_id", "=", module.id),
                ("date_start", "<=", today)
            ], order="date_start desc", limit=1)
            module.current_price = price_record.price if price_record else 0.0

    def _compute_current_price(self):
        users_count = self.env["res.users"].search_count([("share", "=", False)])
        for record in self:
            # 20 nok/min = 1200 nok/hour
            record.current_price = record.minutes_worked * 20 / 100 * sqrt(users_count)

    @api.depends("module_id.name", "version")
    def _compute_name(self):
        for record in self:
            record.name = f"{record.module_id.name or ''} {record.version or ''}"

    module_id = fields.Many2one(
        "ir.module.module",
        string="Module",
        required=True,
        ondelete="cascade",
    )
    module_name = fields.Char(
        related="module_id.name",
    )
    version = fields.Selection(
        [
            ("18", "18"),
            ("19", "19"),
        ],
        string="Version",
        required=True,
    )
    name = fields.Char(
        string="Name",
        compute="_compute_name",
        store=True,
    )
    user_group_id = fields.Many2one(
        "res.groups",
        string="User Group",
        help="Group whose users are counted as active for this app.",
        default=lambda self: self.env.ref("base.group_user", raise_if_not_found=False),
    )
    app_usage_month_ids = fields.One2many(
        "app.usage.month",
        "module_version_id",
        string="Monthly Usage",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    current_price = fields.Monetary(
        string="Price: minutes*20/100*sqrt(users)",
        currency_field="currency_id",
        compute="_compute_current_price",
        help="Latest valid price per user from the App Price List."
    )

    # Temporary, read from csv
    minutes_worked = fields.Integer(
        string="Minutes worked",
    )
    minutes_mig_to_next_version = fields.Integer(
        string="Migration Work (estimated minutes)",
    )
    cost_mig_to_next_version = fields.Monetary(
        string="Cost to migrate",
        compute="_compute_cost_mig_to_next_version",
    )
    total_income = fields.Monetary(
        string="Total Income",
        compute="_compute_financials",
        store=True,
        help="Total income generated from app.usage.month records."
    )
    total_cost = fields.Monetary(
        string="Total Cost",
        compute="_compute_financials",
        store=True,
        help="Total cost based on analytic lines linked to this module."
    )
    total_profit = fields.Monetary(
        string="Total Profit",
        compute="_compute_financials",
        store=True,
        help="Total profit (income minus cost)."
    )

    # Optional link to analytic account (recommended)
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        help="Analytic account for tracking developer costs related to this module."
    )

    # -------------------------------------------------------------
    # Computed fields
    # -------------------------------------------------------------
    @api.depends(
        "app_usage_month_ids.real_price",
        "analytic_account_id.line_ids.amount",
    )
    def _compute_financials(self):
        for module in self:
            # --- Compute total income ---
            usage_lines = self.env["app.usage.month"].search([
                ("module_version_id", "=", module.id)
            ])
            total_income = sum(usage_lines.mapped("real_price"))

            # --- Compute total cost ---
            total_cost = 0.0
            if module.analytic_account_id:
                analytic_lines = self.env["account.analytic.line"].search([
                    ("account_id", "=", module.analytic_account_id.id)
                ])
                total_cost = sum(analytic_lines.mapped("amount"))

            module.total_income = total_income
            module.total_cost = total_cost
            module.total_profit = total_income - total_cost

    @api.model
    def create_missing_versions(self, version=None):
        """Create missing app.module.version records for all installed modules."""
        version = version or odoo.release.version.split(".")[0] # e.g. "18" or "19"

        # 1. Get all installed modules
        installed_modules = self.env["ir.module.module"].search([("state", "=", "installed")])

        if not installed_modules:
            return

        # 2. Get existing versions for these modules (for this version)
        existing_versions = self.search([
            ("version", "=", str(version)),
            ("module_id", "in", installed_modules.ids),
        ])

        existing_module_ids = set(existing_versions.mapped("module_id").ids)

        # 3. Find modules that are missing a version entry
        missing_modules = installed_modules.filtered(lambda m: m.id not in existing_module_ids)

        if not missing_modules:
            return

        # 4. Bulk create all missing records efficiently
        return self.create([
            {"module_id": module.id, "version": str(version)}
            for module in missing_modules
        ])

    @classmethod
    def _read_csv(cls, filepath):
        """Shared CSV reading logic, returns dict[module] = minutes"""
        data = {}
        if not os.path.isfile(filepath):
            return data
        with open(filepath, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                module = row.get("module")
                minutes = row.get("minutes")
                if module and minutes:
                    try:
                        data[module] = int(minutes)
                    except ValueError:
                        continue
        return data

    @api.model
    def import_minutes_worked(self, filepath="../data/modules.csv"):
        """Bulk update minutes_worked from modules.csv"""
        module_minutes = self._read_csv(filepath)
        if not module_minutes:
            return

        existing = self.search([("module_name", "in", list(module_minutes.keys()))])
        for rec in existing:
            minutes = module_minutes.get(rec.module_id.name)
            if minutes is not None:
                rec.minutes_worked = minutes  # uses ORM cache

    @api.model
    def import_migration_minutes(self, filepath):
        """Bulk update minutes_mig_to_next_version from version migration CSV"""
        module_minutes = self._read_csv(filepath)
        if not module_minutes:
            return

        existing = self.search([("module_name", "in", list(module_minutes.keys()))])
        for rec in existing:
            minutes = module_minutes.get(rec.module_id.name)
            if minutes is not None:
                rec.minutes_mig_to_next_version = minutes

    @api.model
    def post_init_hook(self):
        self.create_missing_versions()

        def get_path(relative_path):
            current_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(current_dir, relative_path)
            path = os.path.normpath(path)
            return path

        version = version_info[0]

        self.import_minutes_worked(get_path(f"../data/{version}.csv"))
        self.import_migration_minutes(get_path(f"../oow/{version}-{version + 1}.csv"))
