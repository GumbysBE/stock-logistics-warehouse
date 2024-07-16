# Copyright 2013 Camptocamp SA - Guewen Baconnier
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, exceptions, fields, models


class SaleStockReserve(models.TransientModel):
    _name = "sale.stock.reserve"
    _description = "Sale Stock Reserve"

    @api.model
    def _default_location_id(self):
        domain = [
            "|",
            ("company_id", "=", self.env.company.id),
            ("company_id", "=", False),
        ]
        return self.env["stock.warehouse"].search(domain, limit=1).lot_stock_id

    @api.model
    def _default_location_dest_id(self):
        return self.env["stock.reservation"]._default_location_dest_id()

    def _default_owner(self):
        """If sale_owner_stock_sourcing is installed, it adds an owner field
        on sale order lines. Use it.

        """
        model = self.env[self.env.context["active_model"]]
        if model._name == "sale.order":
            lines = model.browse(self.env.context["active_id"]).order_line
        else:
            lines = model.browse(self.env.context["active_ids"])

        try:
            owners = {line.stock_owner_id for line in lines}
        except AttributeError:
            return self.env["res.partner"]
            # module sale_owner_stock_sourcing not installed, fine

        if len(owners) == 1:
            return owners.pop()
        elif len(owners) > 1:
            raise exceptions.Warning(
                _(
                    """The lines have different owners. Please reserve them
                    individually with the reserve button on each one."""
                )
            )

        return self.env["res.partner"]

    location_id = fields.Many2one(
        "stock.location", "Source Location", required=True, default=_default_location_id
    )
    location_dest_id = fields.Many2one(
        "stock.location",
        "Reservation Location",
        required=True,
        help="Location where the system will reserve the " "products.",
        default=_default_location_dest_id,
    )
    date_validity = fields.Date(
        "Validity Date",
        help="If a date is given, the reservations will be released "
        "at the end of the validity.",
    )
    note = fields.Text("Notes")
    owner_id = fields.Many2one("res.partner", "Stock Owner", default=_default_owner)

    def _prepare_stock_reservation(self, line):
        self.ensure_one()

        return {
            "product_id": line.product_id.id,
            "product_uom": line.product_uom.id,
            "product_uom_qty": line.product_uom_qty,
            "date_validity": self.date_validity,
            "name": f"{line.order_id.name} ({line.name})",
            "location_id": self.location_id.id,
            "location_dest_id": self.location_dest_id.id,
            "note": self.note,
            "price_unit": line.price_unit,
            "sale_line_id": line.id,
            "restrict_partner_id": self.owner_id.id,
        }

    def stock_reserve(self, line_ids):
        self.ensure_one()

        lines = self.env["sale.order.line"].browse(line_ids)
        for line in lines:
            if not line.is_stock_reservable:
                continue
            vals = self._prepare_stock_reservation(line)
            reserv = self.env["stock.reservation"].create(vals)
            reserv.reserve()

    def button_reserve(self):
        self.ensure_one()
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids")
        if not (active_model and active_ids):
            return

        if active_model == "sale.order":
            sales = self.env["sale.order"].browse(active_ids)
            line_ids = sales.order_line.ids

        if active_model == "sale.order.line":
            line_ids = active_ids

        self.stock_reserve(line_ids)
