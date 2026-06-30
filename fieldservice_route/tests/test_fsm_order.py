# Copyright (C) 2026 Gray Matter Logic
# Copyright (C) 2019 Serpent consulting Services
# Copyright 2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from pytz import timezone, utc

from odoo.tests import Form
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.fieldservice.tests.test_fsm_common import FSMCommon


class TestFSMOrderRoute(FSMCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.fsm_route_obj = cls.env["fsm.route"]
        date = datetime.now()
        cls.date = date.replace(microsecond=0)
        cls.days = [
            cls.env.ref("fieldservice_route.fsm_route_day_0").id,
            cls.env.ref("fieldservice_route.fsm_route_day_1").id,
            cls.env.ref("fieldservice_route.fsm_route_day_2").id,
            cls.env.ref("fieldservice_route.fsm_route_day_3").id,
            cls.env.ref("fieldservice_route.fsm_route_day_4").id,
            cls.env.ref("fieldservice_route.fsm_route_day_5").id,
            cls.env.ref("fieldservice_route.fsm_route_day_6").id,
        ]
        cls.fsm_route_id = cls.fsm_route_obj.create(
            {
                "name": "Demo Route",
                "max_order": 10,
                "fsm_person_id": cls.test_person.id,
                "day_ids": [(6, 0, cls.days)],
            }
        )
        cls.test_location.fsm_route_id = cls.fsm_route_id.id

    def test_create_day_route(self):
        order_form = Form(self.env["fsm.order"])
        order_form.location_id = self.test_location
        order_form.scheduled_date_start = self.date
        order = order_form.save()
        self.assertEqual(order.person_id, self.test_person)
        self.assertEqual(order.fsm_route_id, self.test_location.fsm_route_id)
        self.assertEqual(order.dayroute_id.person_id, order.person_id)
        self.assertEqual(order.dayroute_id.date, order.scheduled_date_start.date())
        self.assertEqual(order.dayroute_id.route_id, order.fsm_route_id)

    def test_date_start_planned_uses_worker_schedule(self):
        route_date = self.date.date()
        calendar = self.env["resource.calendar"].create(
            {
                "name": "Early Shift",
                "tz": "US/Eastern",
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Shift",
                            "dayofweek": str(route_date.weekday()),
                            "hour_from": 6.0,
                            "hour_to": 14.0,
                            "day_period": "morning",
                        },
                    )
                ],
            }
        )
        self.test_person.partner_id.tz = "US/Eastern"
        self.test_person.calendar_id = calendar
        dayroute = self.env["fsm.route.dayroute"].create(
            {
                "route_id": self.fsm_route_id.id,
                "date": route_date,
            }
        )
        actual_local = utc.localize(dayroute.date_start_planned).astimezone(
            timezone("US/Eastern")
        )
        self.assertEqual(actual_local.hour, 6)
        self.assertEqual(actual_local.minute, 0)

    def test_date_start_planned_recomputes_on_calendar_change(self):
        route_date = self.date.date()
        calendar = self.env["resource.calendar"].create(
            {
                "name": "Morning Shift",
                "tz": "US/Eastern",
                "attendance_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Shift",
                            "dayofweek": str(route_date.weekday()),
                            "hour_from": 7.0,
                            "hour_to": 15.0,
                            "day_period": "morning",
                        },
                    )
                ],
            }
        )
        self.test_person.partner_id.tz = "US/Eastern"
        self.test_person.calendar_id = calendar
        dayroute = self.env["fsm.route.dayroute"].create(
            {
                "route_id": self.fsm_route_id.id,
                "date": route_date,
            }
        )
        before = utc.localize(dayroute.date_start_planned).astimezone(
            timezone("US/Eastern")
        )
        self.assertEqual(before.hour, 7)
        calendar.attendance_ids.write({"hour_from": 9.0})
        after = utc.localize(dayroute.date_start_planned).astimezone(
            timezone("US/Eastern")
        )
        self.assertEqual(after.hour, 9)

    def test_date_start_planned_fallback_without_calendar(self):
        route_date = self.date.date()
        empty_calendar = self.env["resource.calendar"].create(
            {
                "name": "Empty Schedule",
                "tz": "US/Eastern",
                "attendance_ids": [],
            }
        )
        self.test_person.calendar_id = empty_calendar
        self.test_person.partner_id.tz = "US/Eastern"
        dayroute = self.env["fsm.route.dayroute"].create(
            {
                "route_id": self.fsm_route_id.id,
                "date": route_date,
            }
        )
        actual_local = utc.localize(dayroute.date_start_planned).astimezone(
            timezone("US/Eastern")
        )
        self.assertEqual(actual_local.hour, 8)
        self.assertEqual(actual_local.minute, 0)

    def test_reuse_existing_dayroute(self):
        order1 = self.env["fsm.order"].create(
            {
                "location_id": self.test_location.id,
                "scheduled_date_start": self.date,
                "person_id": self.test_person.id,
            }
        )
        order2 = self.env["fsm.order"].create(
            {
                "location_id": self.test_location.id,
                "scheduled_date_start": self.date,
                "person_id": self.test_person.id,
            }
        )
        self.assertEqual(order1.dayroute_id, order2.dayroute_id)
        self.assertEqual(order1.dayroute_id.order_count, 2)

    def test_order_person_from_route(self):
        order = self.env["fsm.order"].create(
            {
                "location_id": self.test_location.id,
                "scheduled_date_start": self.date,
            }
        )
        self.assertEqual(order.person_id, self.fsm_route_id.fsm_person_id)

    def test_order_sets_route_from_location(self):
        order = self.env["fsm.order"].create(
            {
                "location_id": self.test_location.id,
                "scheduled_date_start": self.date,
            }
        )
        self.assertEqual(order.fsm_route_id, self.test_location.fsm_route_id)

    def test_order_write_scheduled_date_start(self):
        order = self.env["fsm.order"].create(
            {
                "location_id": self.test_location.id,
                "scheduled_date_start": self.date,
                "person_id": self.test_person.id,
            }
        )
        dayroute = order.dayroute_id
        new_date = self.date + timedelta(days=1)
        while new_date.weekday() > 4:
            new_date += timedelta(days=1)
        order.write({"scheduled_date_start": new_date})
        self.assertNotEqual(order.dayroute_id, dayroute)
        self.assertEqual(order.dayroute_id.date, new_date.date())

    def test_get_dayroute_values_string_datetime(self):
        order = self.env["fsm.order"].new({"location_id": self.test_location.id})
        values = order._get_dayroute_values(
            {
                "scheduled_date_start": self.date.strftime(
                    DEFAULT_SERVER_DATETIME_FORMAT
                ),
                "person_id": self.test_person.id,
            }
        )
        self.assertEqual(values["date"], self.date.date())
        self.assertEqual(values["person_id"], self.test_person.id)

    def test_prepare_dayroute_values_and_domain(self):
        order = self.env["fsm.order"].new({"location_id": self.test_location.id})
        values = {
            "person_id": self.test_person.id,
            "date": self.date.date(),
            "route_id": self.fsm_route_id.id,
        }
        prepared = order.prepare_dayroute_values(values)
        self.assertEqual(prepared, values)
        domain = order._get_dayroute_domain(values)
        self.assertEqual(
            domain,
            [
                ("person_id", "=", self.test_person.id),
                ("date", "=", self.date.date()),
                ("order_remaining", ">", 0),
                ("route_id", "=", self.fsm_route_id.id),
            ],
        )
        self.assertTrue(order._can_create_dayroute(values))
        self.assertFalse(
            order._can_create_dayroute({"person_id": False, "date": False})
        )

    def test_manage_fsm_route_skips_create_without_worker(self):
        route = self.fsm_route_obj.create(
            {
                "name": "Route Without Worker",
                "max_order": 5,
                "day_ids": [(6, 0, self.days)],
            }
        )
        location = self.env["fsm.location"].create(
            {
                "name": "Route Location",
                "partner_id": self.test_loc_partner.id,
                "owner_id": self.test_loc_partner.id,
                "fsm_route_id": route.id,
            }
        )
        order = self.env["fsm.order"].new({"location_id": location.id})
        vals = order._manage_fsm_route({"scheduled_date_start": self.date})
        self.assertNotIn("dayroute_id", vals)

    def test_manage_fsm_route_unlinks_empty_dayroute(self):
        order = self.env["fsm.order"].create(
            {
                "location_id": self.test_location.id,
                "scheduled_date_start": self.date,
                "person_id": self.test_person.id,
            }
        )
        old_dayroute = order.dayroute_id
        new_date = self.date + timedelta(days=7)
        while new_date.weekday() > 4:
            new_date += timedelta(days=1)
        order.write({"scheduled_date_start": new_date})
        self.assertNotEqual(order.dayroute_id, old_dayroute)
        self.assertFalse(old_dayroute.exists())

    def test_two_routes_same_worker_same_date(self):
        other_route = self.fsm_route_obj.create(
            {
                "name": "Second Demo Route",
                "max_order": 10,
                "fsm_person_id": self.test_person.id,
                "day_ids": [(6, 0, self.days)],
            }
        )
        other_location = self.env["fsm.location"].create(
            {
                "name": "Second Route Location",
                "partner_id": self.test_loc_partner.id,
                "owner_id": self.test_loc_partner.id,
                "fsm_route_id": other_route.id,
            }
        )
        order1 = self.env["fsm.order"].create(
            {
                "location_id": self.test_location.id,
                "scheduled_date_start": self.date,
                "person_id": self.test_person.id,
            }
        )
        order2 = self.env["fsm.order"].create(
            {
                "location_id": other_location.id,
                "scheduled_date_start": self.date,
                "person_id": self.test_person.id,
            }
        )
        self.assertNotEqual(order1.dayroute_id, order2.dayroute_id)
        self.assertEqual(order1.dayroute_id.route_id, self.fsm_route_id)
        self.assertEqual(order2.dayroute_id.route_id, other_route)

    def test_get_dayroute_values_from_record_scheduled_date(self):
        order = self.env["fsm.order"].create(
            {
                "location_id": self.test_location.id,
                "scheduled_date_start": self.date,
            }
        )
        values = order._get_dayroute_values({})
        self.assertEqual(values["date"], self.date.date())
        self.assertEqual(values["route_id"], self.fsm_route_id.id)

    def test_get_dayroute_values_datetime_object(self):
        order = self.env["fsm.order"].new({"location_id": self.test_location.id})
        values = order._get_dayroute_values(
            {
                "scheduled_date_start": self.date,
                "person_id": self.test_person.id,
                "fsm_route_id": self.fsm_route_id.id,
            }
        )
        self.assertEqual(values["date"], self.date.date())

    def test_create_without_dayroute_assignment(self):
        order = self.env["fsm.order"].create(
            {
                "location_id": self.test_location.id,
            }
        )
        self.assertFalse(order.dayroute_id)

    def test_create_only_scheduled_without_person(self):
        order = self.env["fsm.order"].create(
            {
                "location_id": self.test_location.id,
                "scheduled_date_start": self.date,
            }
        )
        self.assertFalse(order.dayroute_id)

    def test_write_skips_route_management(self):
        order = self.env["fsm.order"].create(
            {
                "location_id": self.test_location.id,
            }
        )
        order.write({"description": "No route update"})

    def test_order_create_multi(self):
        orders = self.env["fsm.order"].create(
            [
                {
                    "location_id": self.test_location.id,
                    "scheduled_date_start": self.date,
                    "person_id": self.test_person.id,
                },
                {
                    "location_id": self.test_location.id,
                    "scheduled_date_start": self.date + timedelta(hours=1),
                    "person_id": self.test_person.id,
                },
            ]
        )
        self.assertEqual(len(orders), 2)
        self.assertEqual(orders[0].dayroute_id, orders[1].dayroute_id)
