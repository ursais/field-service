# Copyright (C) 2026 Gray Matter Logic
# Copyright (C) 2019 Serpent consulting Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    _ROUTE_WRITE_FIELDS = frozenset(
        {
            "person_id",
            "scheduled_date_start",
            "scheduled_date_end",
            "scheduled_duration",
            "location_id",
            "dayroute_id",
        }
    )

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

    def _get_route_id_from_vals(self, vals):
        if vals.get("fsm_route_id"):
            return vals["fsm_route_id"]
        location_id = vals.get("location_id") or self.location_id.id
        if location_id:
            return self.env["fsm.location"].browse(location_id).fsm_route_id.id
        return self.fsm_route_id.id

    def _get_person_id_for_dayroute(self, vals, route_id):
        if vals.get("person_id"):
            return vals["person_id"]
        if route_id:
            route = self.env["fsm.route"].browse(route_id)
            if route.fsm_person_id:
                return route.fsm_person_id.id
        return self.person_id.id or self.fsm_route_id.fsm_person_id.id

    def _get_dayroute_values(self, vals):
        date = False
        if vals.get("scheduled_date_start"):
            if isinstance(vals.get("scheduled_date_start"), str):
                date = datetime.strptime(
                    vals.get("scheduled_date_start"), DEFAULT_SERVER_DATETIME_FORMAT
                ).date()
            elif isinstance(vals.get("scheduled_date_start"), datetime):
                date = vals.get("scheduled_date_start").date()
        route_id = self._get_route_id_from_vals(vals)
        return {
            "person_id": self._get_person_id_for_dayroute(vals, route_id),
            "date": date or self.scheduled_date_start.date(),
            "route_id": route_id,
        }

    def _get_dayroute_domain(self, values):
        return [
            ("person_id", "=", values["person_id"]),
            ("date", "=", values["date"]),
            ("route_id", "=", values.get("route_id") or False),
            ("order_remaining", ">", 0),
        ]

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

    def _prepare_route_write_vals(self, vals):
        write_vals = dict(vals)
        if {
            "scheduled_date_end",
            "scheduled_duration",
            "scheduled_date_start",
        } & write_vals.keys():
            self._calc_scheduled_dates(write_vals)
        return write_vals

    def _is_unscheduling(self, vals):
        return "scheduled_date_start" in vals and not vals.get("scheduled_date_start")

    def _write_with_route_management(self, vals):
        self.ensure_one()
        write_vals = self._prepare_route_write_vals(vals)
        dayroutes_to_check = self.env["fsm.route.dayroute"]

        if self._is_unscheduling(write_vals):
            dayroutes_to_check |= self.dayroute_id
            write_vals["dayroute_id"] = False
            res = super().write(write_vals)
            self._unlink_empty_dayroutes(dayroutes_to_check)
            return res

        if "dayroute_id" in write_vals:
            dayroutes_to_check |= self.dayroute_id
            res = super().write(write_vals)
            self._unlink_empty_dayroutes(dayroutes_to_check)
            return res

        if (write_vals.get("person_id") or self.person_id) and (
            write_vals.get("scheduled_date_start") or self.scheduled_date_start
        ):
            dayroutes_to_check |= self.dayroute_id
            write_vals = self._manage_fsm_route(write_vals)

        res = super().write(write_vals)
        self._unlink_empty_dayroutes(dayroutes_to_check)
        return res

    def write(self, vals):
        route_trigger_fields = self._ROUTE_WRITE_FIELDS | {
            "scheduled_date_end",
            "scheduled_duration",
        }
        if not route_trigger_fields.intersection(vals):
            return super().write(vals)
        if len(self) == 1:
            return self._write_with_route_management(vals)
        for order in self:
            order._write_with_route_management(vals)
        return True
