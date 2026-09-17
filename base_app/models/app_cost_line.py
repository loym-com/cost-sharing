from odoo import models, fields

class AppCostLine(models.Model):
    _name = "app.cost.line"
    _description = "Application Cost Line"
    _order = "id desc"

    module_version_id = fields.Many2one(
        comodel_name="app.module.version",
        string="Module Version",
        required=True,
        ondelete="cascade",
    )

    description = fields.Char(
        string="Description",
        required=False,
        help="Short description of the cost or contribution."
    )

    github_username = fields.Char(
        string="GitHub Username",
        help="Contributor’s GitHub username related to this cost line."
    )

    github_issue_pr = fields.Char(
        string="GitHub Issue/PR",
        help="GitHub issue or pull request reference, e.g. #123 or org/repo#45."
    )

    cost = fields.Monetary(
        string="Cost",
        help="Optional cost amount related to this contribution."
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
