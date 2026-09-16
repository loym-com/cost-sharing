from odoo import fields, models


class MigrationMarketSolveWizard(models.TransientModel):
    _name = "migration.market.solve.wizard"
    _description = "Migration Market Solution"

    result_html = fields.Html(readonly=True)