from collections import defaultdict
from html import escape

from odoo import _, fields, models
from odoo.exceptions import UserError


class MigrationPledge(models.Model):
    _inherit = "migration.market.pledge"

    def action_solve_migration_market(self):
        try:
            from pyscipopt import Model, quicksum
        except ImportError as error:
            raise UserError(
                _("PySCIPOpt must be installed in the Python environment used by Odoo.")
            ) from error

        company = self.env.company
        company_currency = company.currency_id
        today = fields.Date.context_today(self)
        pledges = self.search([("active", "=", True)])
        price_offers = self.env["migration.price"].search([])
        if not pledges:
            raise UserError(_("Create at least one active pledge before solving."))
        if not price_offers:
            raise UserError(_("Create at least one supplier price offer before solving."))

        def to_company_currency(amount, currency):
            return currency._convert(amount, company_currency, company, today)

        def format_amount(amount, currency):
            return "%s %s" % (format(amount, ".2f"), escape(currency.name))

        def table(headers, rows):
            header_html = "".join("<th>%s</th>" % escape(header) for header in headers)
            row_html = "".join(
                "<tr>%s</tr>" % "".join("<td>%s</td>" % value for value in row)
                for row in rows
            )
            return (
                '<table class="table table-sm table-striped"><thead><tr>%s</tr>'
                "</thead><tbody>%s</tbody></table>"
            ) % (header_html, row_html)

        offers = list(price_offers)
        offers_by_module = defaultdict(list)
        offers_by_supplier = defaultdict(list)
        converted_price = {}
        for offer in offers:
            offers_by_module[offer.module_id.id].append(offer)
            offers_by_supplier[offer.supplier_id.id].append(offer)
            converted_price[offer.id] = to_company_currency(
                offer.price, offer.currency_id
            )
        best_score_by_module = {
            module_id: max(offer.supplier_id.migration_supplier_score for offer in module_offers)
            for module_id, module_offers in offers_by_module.items()
        }

        solver = Model("migration_market")
        solver.hideOutput()
        assignments = {
            (offer.supplier_id.id, offer.module_id.id): solver.addVar(
                vtype="B", name=f"assignment_{offer.id}"
            )
            for offer in offers
        }
        activated = {
            pledge.id: solver.addVar(vtype="B", name=f"activated_{pledge.id}")
            for pledge in pledges
        }

        for module_id, module_offers in offers_by_module.items():
            solver.addCons(
                quicksum(
                    assignments[offer.supplier_id.id, module_id]
                    for offer in module_offers
                )
                <= 1,
                name=f"module_{module_id}_once",
            )

        pledge_offers_by_id = {}
        pledge_count_by_module = defaultdict(int)
        for pledge in pledges:
            pledge_offers = [
                offer
                for module in pledge.module_ids
                for offer in offers_by_module[module.id]
            ]
            pledge_offers_by_id[pledge.id] = pledge_offers
            for module in pledge.module_ids:
                pledge_count_by_module[module.id] += 1
                solver.addCons(
                    activated[pledge.id]
                    <= quicksum(
                        assignments[offer.supplier_id.id, module.id]
                        for offer in offers_by_module[module.id]
                    ),
                    name=f"pledge_{pledge.id}_module_{module.id}_required",
                )

        for supplier_offers in offers_by_supplier.values():
            supplier = supplier_offers[0].supplier_id
            solver.addCons(
                quicksum(
                    converted_price[offer.id]
                    * assignments[offer.supplier_id.id, offer.module_id.id]
                    for offer in supplier_offers
                )
                <= to_company_currency(
                    supplier.migration_supplier_capacity,
                    supplier.migration_currency_id,
                ),
                name=f"supplier_{supplier.id}_capacity",
            )

        pledge_assignments = {}
        customer_values = []
        for pledge in pledges:
            pledge_offers = pledge_offers_by_id[pledge.id]
            score_sum = quicksum(
                offer.supplier_id.migration_supplier_score
                * assignments[offer.supplier_id.id, offer.module_id.id]
                for offer in pledge_offers
            )
            solver.addCons(
                score_sum / len(pledge.module_ids)
                >= pledge.minimum_score - (1 - activated[pledge.id]),
                name=f"pledge_{pledge.id}_minimum_score",
            )
            for offer in pledge_offers:
                variable = solver.addVar(vtype="B", name=f"pledge_{pledge.id}_offer_{offer.id}")
                pledge_assignments[pledge.id, offer.id] = variable
                assignment = assignments[offer.supplier_id.id, offer.module_id.id]
                solver.addCons(variable <= activated[pledge.id])
                solver.addCons(variable <= assignment)
                solver.addCons(variable >= activated[pledge.id] + assignment - 1)

            wtp = to_company_currency(pledge.wtp, pledge.currency_id)
            # Quality-adjusted price = price * (best_score_for_module / score) ** value_of_quality,
            # so the best-scored supplier for a module is never penalized (bonus 0) and weaker
            # suppliers are penalized relative to it, justifying a higher price for higher score.
            # Divided by the number of pledges requesting the module so the combined bonus for a
            # shared module scales like its shared cost instead of being multiplied per pledge.
            quality_bonus = quicksum(
                converted_price[offer.id]
                * (
                    1
                    - (
                        best_score_by_module[offer.module_id.id]
                        / offer.supplier_id.migration_supplier_score
                    )
                    ** pledge.value_of_quality
                )
                / pledge_count_by_module[offer.module_id.id]
                * pledge_assignments[pledge.id, offer.id]
                for offer in pledge_offers
            )
            customer_values.append(wtp * activated[pledge.id] + quality_bonus)

        migration_cost = quicksum(
            converted_price[offer.id]
            * assignments[offer.supplier_id.id, offer.module_id.id]
            for offer in offers
        )
        primary_objective = quicksum(customer_values) - migration_cost
        solver.setObjective(primary_objective, "maximize")
        solver.optimize()
        if str(solver.getStatus()) != "optimal":
            raise UserError(_("No optimal solution was found: %s") % solver.getStatus())

        primary_objective_value = solver.getObjVal()
        solver.freeTransform()
        solver.addCons(
            primary_objective >= primary_objective_value - 0.000001,
            name="preserve_primary_objective",
        )
        solver.setObjective(quicksum(activated.values()), "maximize")
        solver.optimize()
        if str(solver.getStatus()) != "optimal":
            raise UserError(
                _("No optimal tie-breaker solution was found: %s") % solver.getStatus()
            )

        selected_offers = [
            offer
            for offer in offers
            if solver.getVal(assignments[offer.supplier_id.id, offer.module_id.id]) > 0.5
        ]
        selected_offer_ids = {offer.id for offer in selected_offers}
        selected_module_ids = {offer.module_id.id for offer in selected_offers}
        requested_modules = {
            module.id: module
            for pledge in pledges
            for module in pledge.module_ids
        }
        unselected_modules = [
            module
            for module_id, module in requested_modules.items()
            if module_id not in selected_module_ids
        ]
        active_pledges = [
            pledge for pledge in pledges if solver.getVal(activated[pledge.id]) > 0.5
        ]

        # Every active pledge pays the same ratio of its own willingness to pay, so the
        # total collected matches the total migration cost.
        active_wtp = {
            pledge.id: to_company_currency(pledge.wtp, pledge.currency_id)
            for pledge in active_pledges
        }
        total_cost = sum(converted_price[offer.id] for offer in selected_offers)
        total_wtp = sum(active_wtp.values())
        if total_cost and not total_wtp:
            raise UserError(_("Accepted offers cannot be covered by active pledges."))
        payment_ratio = total_cost / total_wtp if total_wtp else 0
        if payment_ratio > 1 and not company_currency.is_zero(total_cost - total_wtp):
            raise UserError(_("Accepted offers cannot be covered by active pledges."))
        payments = {
            pledge.id: payment_ratio * active_wtp[pledge.id]
            if pledge in active_pledges
            else 0
            for pledge in pledges
        }

        pledge_rows = [
            (
                escape(pledge.partner_id.display_name),
                escape(", ".join(pledge.module_ids.mapped("display_name"))),
                format_amount(pledge.wtp, pledge.currency_id),
                format(pledge.value_of_quality, ".2f"),
                # format(pledge.minimum_score, ".2f"),
                format_amount(payments[pledge.id], company_currency),
                escape(
                    _("Activated")
                    if solver.getVal(activated[pledge.id]) > 0.5
                    else _("Not activated")
                ),
            )
            for pledge in pledges
        ]
        price_offer_rows = [
            (
                escape(offer.supplier_id.display_name),
                escape(offer.module_id.display_name),
                format(offer.supplier_score, ".2f"),
                # format_amount(offer.supplier_capacity, offer.currency_id),
                format_amount(offer.price, offer.currency_id),
                escape(_("Accepted") if offer.id in selected_offer_ids else ""),
            )
            for offer in offers
        ]
        migration_rows = [
            (
                escape(offer.module_id.display_name),
                escape(offer.supplier_id.display_name),
                format_amount(offer.price, offer.currency_id),
            )
            for offer in selected_offers
        ]
        not_migrated_rows = [(escape(module.display_name),) for module in unselected_modules]
        report_html = "".join(
            [
                "<h2>%s</h2>" % escape(_("Demand")),
                table(
                    [
                        _("Customer"),
                        _("Modules"),
                        _("Willing to Pay"),
                        _("Value of Quality"),
                        # _("Minimum Score"),
                        _("Payment"),
                        _("Status"),
                    ],
                    pledge_rows,
                ),
                # "<p><strong>%s:</strong> %s</p>"
                # % (
                #     escape(_("Total pledge payments")),
                #     format_amount(sum(payments.values()), company_currency),
                # ),
                "<h2>%s</h2>" % escape(_("Supply")),
                table(
                    [
                        _("Supplier"),
                        _("Module"),
                        _("Quality"),
                        # _("Capacity"),
                        _("Price"),
                        _("Status"),
                    ],
                    price_offer_rows,
                ),
                "<h2>%s</h2>" % escape(_("Modules to Migrate")),
                table([_("Module"), _("Supplier"), _("Price")], migration_rows),
                "<h2>%s</h2>" % escape(_("Modules Not Migrated")),
                table([_("Module")], not_migrated_rows),
            ]
        )
        wizard = self.env["migration.market.solve.wizard"].create(
            {"result_html": report_html}
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "migration.market.solve.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
