from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cs_weight_rating = fields.Float(
        string="Rating weight (%)", default=25.0, config_parameter="cost_sharing.weight_rating"
    )
    cs_weight_author = fields.Float(
        string="Author weight (%)", default=25.0, config_parameter="cost_sharing.weight_author"
    )
    cs_weight_contributor = fields.Float(
        string="Contributor weight (%)",
        default=25.0,
        config_parameter="cost_sharing.weight_contributor",
    )
    cs_weight_maintainer = fields.Float(
        string="Maintainer weight (%)",
        default=25.0,
        config_parameter="cost_sharing.weight_maintainer",
    )
    cs_margin = fields.Float(
        string="Marketplace margin (%)", default=10.0, config_parameter="cost_sharing.margin"
    )
