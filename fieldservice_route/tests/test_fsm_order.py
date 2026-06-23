# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent consulting Services
# Copyright 2022 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from datetime import datetime

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
