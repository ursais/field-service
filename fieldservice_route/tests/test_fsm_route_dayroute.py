# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent consulting Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime, timedelta
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tools import mute_logger

from odoo.addons.fieldservice.tests.test_fsm_common import FSMCommon


class TestFSMRouteDayRoute(FSMCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.DayRoute = cls.env["fsm.route.dayroute"]
        cls.Route = cls.env["fsm.route"]
        cls.monday = cls.env.ref("fieldservice_route.fsm_route_day_0")
        cls.route = cls.Route.create(
            {
                "name": "Worker Route",
                "max_order": 5,
                "fsm_person_id": cls.test_person.id,
                "day_ids": [(6, 0, [cls.monday.id])],
            }
        )

    def _next_weekday(self, weekday):
        date = datetime.now().date()
        while date.weekday() != weekday:
            date += timedelta(days=1)
        return date

    def test_default_team_required(self):
        with mute_logger("odoo.models.unlink"):
            self.env["fsm.team"].search([]).unlink()
        with self.assertRaisesRegex(
            ValidationError, "You must create a FSM team first."
        ):
            self.DayRoute.create(
                {
                    "route_id": self.route.id,
                    "date": self._next_weekday(0),
                }
            )

    def test_person_without_route_worker(self):
        route = self.Route.create(
            {
                "name": "Unstaffed Route",
                "day_ids": [(6, 0, [self.monday.id])],
            }
        )
        dayroute = self.DayRoute.create(
            {
                "route_id": route.id,
                "date": self._next_weekday(0),
            }
        )
        self.assertFalse(dayroute.person_id)

    def test_compute_date_start_planned_without_date(self):
        dayroute = self.DayRoute.new({"route_id": self.route.id})
        dayroute._compute_date_start_planned()
        self.assertFalse(dayroute.date_start_planned)

    def test_create_without_route_id_with_person(self):
        route_date = self._next_weekday(0)
        dayroute = self.DayRoute.create(
            {
                "date": route_date,
                "person_id": self.test_person.id,
            }
        )
        self.assertTrue(dayroute.date_start_planned)

    def test_planned_start_uses_route_worker(self):
        route_date = self._next_weekday(0)
        planned = self.DayRoute._planned_start_from_date(
            route_date,
            route=self.route,
        )
        self.assertTrue(planned)

    def test_planned_start_company_calendar_timezone(self):
        route_date = self._next_weekday(0)
        self.test_person.partner_id.tz = False
        self.test_person.calendar_id = False
        self.env.company.resource_calendar_id.tz = "UTC"
        planned = self.DayRoute._planned_start_from_date(
            route_date,
            person=self.test_person,
            route=self.route,
        )
        self.assertTrue(planned)

    def test_planned_start_user_timezone_fallback(self):
        route_date = self._next_weekday(0)
        self.test_person.partner_id.tz = False
        self.test_person.calendar_id = False
        calendar = self.env.company.resource_calendar_id
        with (
            patch.object(type(calendar), "_get_closest_work_time", return_value=None),
            patch.object(type(calendar), "tz", False),
            patch.object(type(self.env.user), "tz", False),
        ):
            planned = self.DayRoute._planned_start_from_date(
                route_date,
                person=self.test_person,
                route=self.route,
            )
        self.assertTrue(planned)

    def test_check_day_skipped_without_route_or_date(self):
        dayroute = self.DayRoute.new({})
        dayroute.check_day()

    def test_create_without_route_id(self):
        route_date = self._next_weekday(0)
        dayroute = self.DayRoute.create({"date": route_date})
        self.assertTrue(dayroute.date_start_planned)

    def test_compute_date_start_clears_without_date(self):
        dayroute = self.DayRoute.create(
            {
                "route_id": self.route.id,
                "date": self._next_weekday(0),
            }
        )
        dayroute.write({"date": False})
        self.assertFalse(dayroute.date_start_planned)

    def test_planned_start_without_work_interval(self):
        route_date = self._next_weekday(0)
        calendar = self.env["resource.calendar"].create(
            {
                "name": "No Attendance",
                "tz": "UTC",
                "attendance_ids": [],
            }
        )
        self.test_person.calendar_id = calendar
        with patch.object(type(calendar), "_get_closest_work_time", return_value=None):
            planned = self.DayRoute._planned_start_from_date(
                route_date,
                person=self.test_person,
                route=self.route,
            )
        self.assertTrue(planned)

    def test_dayroute_create_with_date_start_planned(self):
        route_date = self._next_weekday(0)
        planned = self.DayRoute._planned_start_from_date(
            route_date,
            route=self.route,
        )
        dayroute = self.DayRoute.create(
            {
                "route_id": self.route.id,
                "date": route_date,
                "date_start_planned": planned,
            }
        )
        self.assertEqual(dayroute.date_start_planned, planned)

    def test_compute_date_start_uses_dayroute_person(self):
        other_person = self.env["fsm.person"].create({"name": "Other Worker"})
        dayroute = self.DayRoute.create(
            {
                "route_id": self.route.id,
                "date": self._next_weekday(0),
                "person_id": other_person.id,
            }
        )
        dayroute.invalidate_recordset(["date_start_planned"])
        dayroute._compute_date_start_planned()
        self.assertTrue(dayroute.date_start_planned)

    def test_portal_user_sees_only_own_dayroutes(self):
        other_person = self.env["fsm.person"].create({"name": "Other Worker"})
        route_date = self._next_weekday(0)
        own_dayroute = self.DayRoute.create(
            {
                "route_id": self.route.id,
                "date": route_date,
            }
        )
        other_route = self.Route.create(
            {
                "name": "Other Worker Route",
                "max_order": 5,
                "fsm_person_id": other_person.id,
                "day_ids": [(6, 0, [self.monday.id])],
            }
        )
        other_dayroute = self.DayRoute.create(
            {
                "route_id": other_route.id,
                "date": route_date,
            }
        )
        portal_user = self.env["res.users"].create(
            {
                "name": self.test_person.name,
                "login": "portal_route_worker",
                "partner_id": self.test_person.partner_id.id,
                "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        portal_dayroutes = self.DayRoute.with_user(portal_user).search([])
        self.assertIn(own_dayroute, portal_dayroutes)
        self.assertNotIn(other_dayroute, portal_dayroutes)

    def test_create_sequence_fallback(self):
        route_date = self._next_weekday(0)
        with patch.object(
            type(self.env["ir.sequence"]),
            "next_by_code",
            return_value=False,
        ):
            dayroute = self.DayRoute.create(
                {
                    "route_id": self.route.id,
                    "date": route_date,
                }
            )
        self.assertEqual(dayroute.name, "New")
