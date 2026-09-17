from math import sqrt
from odoo import models, fields, api
from datetime import date


class AppPriceList(models.Model):
    _name = "app.pricelist"
    _description = "App Yearly Price List"

    module_id = fields.Many2one(
        "ir.module.module",
        string="Module",
        required=True,
        ondelete="cascade",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id.id,
    )

    price = fields.Monetary(
        string="Base price/year",
        required=True,
        help="Base price for one user for this app."
    )

    date_start = fields.Date(
        string="Start Date",
        required=True,
        default=fields.Date.context_today,
        help="Date from which this price is valid."
    )

    _sql_constraints = [
        (
            "unique_module_start_date",
            "unique(module_id, date_start)",
            "There can be only one price per module per start date.",
        )
    ]

    # -------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------
    # def get_price_for_month(self, month_date):
    #     """
    #     Returns the price applicable for the module in the given month.
    #     Chooses the latest date_start <= month_date.
    #     """
    #     self.ensure_one()
    #     price_record = self.search([
    #         ("module_id", "=", self.module_id.id),
    #         ("date_start", "<=", month_date),
    #     ], order="date_start desc", limit=1)
    #     return price_record.price if price_record else self.price

    # def compute_real_price(self, month_date, month_fraction):
    #     """
    #     Computes the real price for a month using square root formula:
    #     real_price = base_price * sqrt(month_fraction)
    #     """
    #     price = self.get_price_for_month(month_date)
    #     return price * sqrt(month_fraction)
