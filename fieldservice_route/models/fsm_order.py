# Copyright (C) 2026 Gray Matter Logic
# Copyright (C) 2019 Serpent consulting Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    dayroute_id = fields.Many2one(
        comodel_name="fsm.route.dayroute", string="Day Route", index=True
    )
    fsm_route_id = fields.Many2one(related="location_id.fsm_route_id", string="Route")

    person_id = fields.Many2one(
        comodel_name="fsm.person",
        string="Assigned To",
        index=True,
        compute="_compute_person_id",
        store=True,
        readonly=False,
    )

    @api.depends("fsm_route_id")
    def _compute_person_id(self):
        for item in self.filtered("fsm_route_id"):
            item.person_id = item.fsm_route_id.fsm_person_id

    def prepare_dayroute_values(self, values):
        return {
            "person_id": values["person_id"],
            "date": values["date"],
            "route_id": values["route_id"],
        }

    def _get_dayroute_values(self, vals):
        date = False
        if vals.get("scheduled_date_start"):
            if isinstance(vals.get("scheduled_date_start"), str):
                date = datetime.strptime(
                    vals.get("scheduled_date_start"), DEFAULT_SERVER_DATETIME_FORMAT
                ).date()
            elif isinstance(vals.get("scheduled_date_start"), datetime):
                date = vals.get("scheduled_date_start").date()
        return {
            "person_id": vals.get("person_id")
            or self.person_id.id
            or self.fsm_route_id.fsm_person_id.id,
            "date": date or self.scheduled_date_start.date(),
            "route_id": vals.get("fsm_route_id") or self.fsm_route_id.id,
        }

    def _get_dayroute_domain(self, values):
        domain = [
            ("person_id", "=", values["person_id"]),
            ("date", "=", values["date"]),
            ("order_remaining", ">", 0),
        ]
        if values.get("route_id"):
            domain.append(("route_id", "=", values["route_id"]))
        return domain

    def _can_create_dayroute(self, values):
        return values["person_id"] and values["date"]

    def _unlink_empty_dayroutes(self, dayroutes):
        dayroutes.filtered(
            lambda dayroute: dayroute and not dayroute.order_ids
        ).unlink()

    def _manage_fsm_route(self, vals):
        dayroute_obj = self.env["fsm.route.dayroute"]
        values = self._get_dayroute_values(vals)
        domain = self._get_dayroute_domain(values)
        dayroute = dayroute_obj.search(domain, limit=1)
        if dayroute:
            vals.update({"dayroute_id": dayroute.id})
        elif self._can_create_dayroute(values):
            dayroute = dayroute_obj.create(self.prepare_dayroute_values(values))
            vals.update({"dayroute_id": dayroute.id})
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("fsm_route_id") and vals.get("location_id"):
                location = self.env["fsm.location"].browse(vals["location_id"])
                vals.update({"fsm_route_id": location.fsm_route_id.id})

            if vals.get("person_id") and vals.get("scheduled_date_start"):
                vals = self._manage_fsm_route(vals)
        return super().create(vals_list)

    def write(self, vals):
        dayroutes_to_check = self.env["fsm.route.dayroute"]
        for rec in self:
            if (vals.get("person_id", False) or rec.person_id) and (
                vals.get("scheduled_date_start", False) or rec.scheduled_date_start
            ):
                dayroutes_to_check |= rec.dayroute_id
                vals = rec._manage_fsm_route(vals)
        res = super().write(vals)
        self._unlink_empty_dayroutes(dayroutes_to_check)
        return res
