from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    cs_app_id = fields.Many2one("ir.module.module", string="Odoo app")


class ProductProduct(models.Model):
    _inherit = "product.product"

    cs_app_id = fields.Many2one(related="product_tmpl_id.cs_app_id", store=True, readonly=True)


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    cs_hours = fields.Float(string="Migration hours")
    cs_hours_computed = fields.Float(string="Computed migration hours", readonly=True)
    cs_price_computed = fields.Monetary(
        string="Computed migration price", currency_field="currency_id", readonly=True
    )

    def compute_cost_sharing_values(self):
        """Prepare the offer for future solver calculations."""
        self.write({"cs_hours_computed": 0.0, "cs_price_computed": 0.0})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.compute_cost_sharing_values()
        return records
