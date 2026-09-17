from calendar import monthrange
from datetime import date
from dateutil.relativedelta import relativedelta
from math import sqrt

from odoo import api, fields, models


class AppUsageMonth(models.Model):
    _name = "app.usage.month"
    _description = "Monthly App Usage Summary"
    _order = "year desc, month desc, module_version_id"

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
    #     help="Contract under which this app is billed.",
    # )

    year = fields.Integer(required=True)
    month = fields.Integer(required=True)
    average_users = fields.Float(string="Average Users")
    month_fraction = fields.Float(string="Month Fraction")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )
    base_price = fields.Monetary(
        string="Base price",
        help="List price applied to this month (copied from pricelist)."
    )
    real_price = fields.Monetary(
        string="Real Price",
        help="Base price * sqrt(user days / days) * days / days in month"
    )

    # _sql_constraints = [
    #     (
    #         "unique_module_month",
    #         "unique(module_version_id, contract_id, year, month)",
    #         "Each module + contract can have only one monthly usage summary.",
    #     )
    # ]

    # -------------------------------------------------------------
    # Monthly aggregation cron 
    # -------------------------------------------------------------
    @api.model
    def cron_aggregate_monthly_usage(self):
        """Aggregate daily usage lines and compute prices for the previous month."""
        UsageLine = self.env["app.usage.line"]
        PriceList = self.env["app.pricelist"]

        today = date.today()
        last_month = today - relativedelta(months=1)
        year, month = last_month.year, last_month.month

        # Period boundaries
        first_day = date(year, month, 1)
        next_month = first_day + relativedelta(months=1)
        days_in_month = (next_month - first_day).days
        # days_in_month = monthrange(year, month)[1]

        # Aggregate daily usage per module + contract
        self.env.cr.execute("""
            SELECT module_version_id, SUM(active_users) AS total_user_days, COUNT(id) AS count_days
            FROM app_usage_line
            WHERE date >= %s AND date < %s
            GROUP BY module_version_id
        """, (first_day, next_month))

        totals = self.env.cr.fetchall()
        if not totals:
            return

        # Avoid duplicates
        existing = self.search([
            ("year", "=", year),
            ("month", "=", month),
        ])
        # existing_keys = {(rec.module_version_id.id, rec.contract_id.id or 0) for rec in existing}
        existing_keys = {(rec.module_version_id.id) for rec in existing}

        records_to_create = []

        for module_version_id, total_user_days, count_days in totals:
            key = (module_version_id)
            if key in existing_keys:
                continue

            average_users = total_user_days / count_days
            month_fraction = count_days / days_in_month

            # Determine list price for this month
            price_record = PriceList.search([
                ("module_version_id", "=", module_version_id),
                ("date_start", "<=", first_day)
            ], order="date_start desc", limit=1)
            base_price = price_record.price if price_record else 0.0

            if days_in_month:
                real_price = base_price * sqrt(average_users) * month_fraction

                records_to_create.append({
                    "module_version_id": module_version_id,
                    # "contract_id": contract_id,
                    "year": year,
                    "month": month,
                    "average_users": average_users,
                    "month_fraction": month_fraction,
                    "base_price": base_price,
                    "real_price": real_price,
                })

        if records_to_create:
            self.create(records_to_create)
