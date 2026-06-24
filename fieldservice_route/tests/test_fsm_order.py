# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent consulting Services
# Copyright 2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta

from pytz import timezone, utc

from odoo.tests import Form

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
