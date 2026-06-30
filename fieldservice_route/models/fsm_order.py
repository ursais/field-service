# Copyright (C) 2026 Gray Matter Logic
# Copyright (C) 2019 Serpent consulting Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime, time

from pytz import timezone, utc

from odoo import api, fields, models
from odoo.exceptions import ValidationError


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

    @api.depends("fsm_route_id", "fsm_route_id.fsm_person_id")
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

    def _tz_name_for_route_day(self, person=None, route=None):
        person = person or self.env["fsm.person"]
        route = route or self.env["fsm.route"]
        return (
            (person.partner_id.tz if person else False)
            or (route.fsm_person_id.partner_id.tz if route.fsm_person_id else False)
            or self.env.user.tz
            or "UTC"
        )

    def _local_date_from_scheduled_start(
        self, scheduled_start, person=None, route=None
    ):
        """Return the worker/route local calendar day for a UTC-naive datetime."""
        start = fields.Datetime.to_datetime(scheduled_start)
        if not start:
            return False
        tzinfo = timezone(self._tz_name_for_route_day(person=person, route=route))
        return utc.localize(start).astimezone(tzinfo).date()

    def _scheduled_start_on_dayroute_date(self, current_start, dayroute, person=None):
        """Move a UTC-naive start onto the dayroute date in the worker timezone."""
        person = person or dayroute.person_id
        tzinfo = timezone(
            self._tz_name_for_route_day(person=person, route=dayroute.route_id)
        )
        if current_start:
            local = utc.localize(fields.Datetime.to_datetime(current_start)).astimezone(
                tzinfo
            )
            local = local.replace(
                year=dayroute.date.year,
                month=dayroute.date.month,
                day=dayroute.date.day,
            )
            return local.astimezone(utc).replace(tzinfo=None)
        if dayroute.date_start_planned:
            return dayroute.date_start_planned
        local = tzinfo.localize(datetime.combine(dayroute.date, time(8, 0)))
        return local.astimezone(utc).replace(tzinfo=None)

    def _get_dayroute_values(self, vals):
        route_id = self._get_route_id_from_vals(vals)
        person_id = self._get_person_id_for_dayroute(vals, route_id)
        person = (
            self.env["fsm.person"].browse(person_id) if person_id else self.person_id
        )
        route = (
            self.env["fsm.route"].browse(route_id) if route_id else self.fsm_route_id
        )
        scheduled_start = vals.get("scheduled_date_start") or self.scheduled_date_start
        date = self._local_date_from_scheduled_start(
            scheduled_start, person=person, route=route
        )
        return {
            "person_id": person_id,
            "date": date,
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

            if vals.get("dayroute_id"):
                order = self.new(vals)
                dayroute = self.env["fsm.route.dayroute"].browse(vals["dayroute_id"])
                vals.update(order._prepare_vals_from_dayroute(dayroute, vals))
            elif vals.get("person_id") and vals.get("scheduled_date_start"):
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
            # Include start when only end was derived so super().write()'s
            # second _calc_scheduled_dates takes the start+end branch.
            # Otherwise duration 0 is falsy and the end-only branch recomputes
            # start from the still-unwritten previous duration.
            if (
                write_vals.get("scheduled_date_end")
                and "scheduled_date_start" not in write_vals
                and self.scheduled_date_start
            ):
                write_vals["scheduled_date_start"] = self.scheduled_date_start
        return write_vals

    def _is_unscheduling(self, vals):
        return "scheduled_date_start" in vals and not vals.get("scheduled_date_start")

    def _order_route_for_dayroute_write(self, write_vals):
        location_id = write_vals.get("location_id") or self.location_id.id
        if location_id:
            return self.env["fsm.location"].browse(location_id).fsm_route_id
        return self.fsm_route_id

    def _prepare_vals_from_dayroute(self, dayroute, write_vals):
        """Make an explicit day route authoritative for person and schedule date."""
        write_vals = dict(write_vals)
        if not dayroute:
            return write_vals
        order_route = self._order_route_for_dayroute_write(write_vals)
        if dayroute.route_id and order_route and dayroute.route_id != order_route:
            raise ValidationError(
                self.env._(
                    "The day route %(dayroute)s belongs to route %(route)s, "
                    "which does not match the order route %(order_route)s.",
                    dayroute=dayroute.display_name,
                    route=dayroute.route_id.display_name,
                    order_route=order_route.display_name,
                )
            )
        if dayroute.person_id:
            write_vals["person_id"] = dayroute.person_id.id
        if dayroute.date:
            current_start = (
                write_vals.get("scheduled_date_start") or self.scheduled_date_start
            )
            write_vals["scheduled_date_start"] = self._scheduled_start_on_dayroute_date(
                current_start,
                dayroute,
                person=dayroute.person_id,
            )
        return write_vals

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
            new_dayroute = self.env["fsm.route.dayroute"].browse(
                write_vals.get("dayroute_id") or []
            )
            write_vals = self._prepare_vals_from_dayroute(new_dayroute, write_vals)
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
