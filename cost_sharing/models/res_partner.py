from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    cs_partner = fields.Boolean(string="Marketplace partner")
    cs_hours_per_week = fields.Integer(string="Marketplace capacity (hours/week)")
    cs_currency_id = fields.Many2one(
        "res.currency", compute="_compute_cs_currency_id", string="Marketplace currency"
    )
    cs_hour_price = fields.Monetary(string="Hourly price", currency_field="cs_currency_id")
    cs_price_py = fields.Monetary(string="Python line price", currency_field="cs_currency_id")
    cs_price_js = fields.Monetary(string="JavaScript line price", currency_field="cs_currency_id")
    cs_price_xml = fields.Monetary(string="XML line price", currency_field="cs_currency_id")
    cs_price_fixed = fields.Monetary(string="Fixed price", currency_field="cs_currency_id")
    cs_rate_ids = fields.One2many("res.partner.rate", "to_partner_id", string="Received ratings")
    cs_github_ids = fields.One2many("res.partner.github", "partner_id", string="GitHub names")
    cs_repo_ids = fields.One2many("res.partner.repo", "partner_id", string="Repositories")
    cs_supply_ids = fields.One2many("cs.partner.supply", "partner_id", string="Supplies")

    @api.depends("company_id")
    def _compute_cs_currency_id(self):
        for partner in self:
            partner.cs_currency_id = (
                partner.company_id.currency_id or self.env.company.currency_id
            )


class ResPartnerRate(models.Model):
    _name = "res.partner.rate"
    _description = "Cost Sharing Partner Rating"
    _rec_name = "name"
    _sql_constraints = [
        (
            "unique_from_to_partner",
            "unique(from_partner_id, to_partner_id)",
            "A partner can rate another partner only once.",
        ),
    ]

    name = fields.Char(compute="_compute_name", store=True)
    rate = fields.Selection(
        [("0", "0 stars"), ("1", "1 star"), ("2", "2 stars"), ("3", "3 stars")],
        default="1",
        required=True,
    )
    from_partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    to_partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")

    @api.depends("from_partner_id", "to_partner_id", "rate")
    def _compute_name(self):
        for rating in self:
            rating.name = "%s %s %s" % (
                rating.from_partner_id.display_name,
                rating.to_partner_id.display_name,
                rating.rate or "",
            )

    @api.constrains("from_partner_id", "to_partner_id")
    def _check_different_partners(self):
        if any(rating.from_partner_id == rating.to_partner_id for rating in self):
            raise ValidationError("A partner cannot rate itself.")

    @api.constrains("rate", "from_partner_id")
    def _check_outgoing_average(self):
        for rating in self:
            ratings = self.search([("from_partner_id", "=", rating.from_partner_id.id)])
            if ratings and sum(int(item.rate) for item in ratings) / len(ratings) < 1:
                raise ValidationError("Your ratings must have an average of at least 1 star.")


class ResPartnerGithub(models.Model):
    _name = "res.partner.github"
    _description = "Cost Sharing GitHub Name"
    _rec_name = "name"
    _sql_constraints = [
        ("unique_github_name", "unique(name)", "A GitHub name can only be registered once."),
    ]

    name = fields.Char(required=True)
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    state = fields.Selection(
        [("draft", "Draft"), ("verified", "Verified")], default="draft", required=True
    )


class ResPartnerRepo(models.Model):
    _name = "res.partner.repo"
    _description = "Cost Sharing Repository"
    _rec_name = "url"

    url = fields.Char(string="Repository URL", required=True)
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    state = fields.Selection(
        [("draft", "Draft"), ("verified", "Verified")], default="draft", required=True
    )


class CostSharingPartnerSupply(models.Model):
    _name = "cs.partner.supply"
    _description = "Cost Sharing Partner Supply"

    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    attribute_value_id = fields.Many2one("product.attribute.value", required=True)
    app_id = fields.Many2one("ir.module.module")
    price = fields.Monetary(currency_field="currency_id", required=True)
    currency_id = fields.Many2one(related="partner_id.cs_currency_id", readonly=True)
