# Copyright 2013 Camptocamp SA - Guewen Baconnier
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models

class ProductProduct(models.Model):
    _inherit = "product.product"

    def _compute_reservation_count(self):
        for product in self:
            domain = [
                ("product_id", "=", product.id),
                ("state", "in", ["draft", "assigned", "confirmed"]),
            ]
            reservations = self.env["stock.reservation"].search(domain)
            product.reservation_count = sum(reservations.mapped("product_qty"))
