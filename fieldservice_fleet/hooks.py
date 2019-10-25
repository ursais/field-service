# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Brian McMaster
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import SUPERUSER_ID, api, _


def post_init_hook(cr, registry):

    logging.getLogger('odoo.addons.fieldservice_fleet').info(
        'Migrating existing FSM Vehicle to Fleet Vehicle')

    env = api.Environment(cr, SUPERUSER_ID, {})

    vehicles = env['fsm.vehicle'].search([('fleet_vehicle_id', '=', False)])

    if vehicles:
        # Get the first vehicle model available
        model = env['fleet.vehicle.model'].search(limit=1)

        fleet = env['fleet.vehicle']

        # Create a Fleet vehicle for each existing FSM vehicle
        for vehicle in vehicles:
            new = fleet.create({
                'model_id': model.id
                'driver_id': vehicle.person_id.id or False,
                'is_fsm_vehicle': True,
            })
            vehicle.fleet_vehicle_id = new.id
