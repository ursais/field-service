# Copyright (C) 2019, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class FSMOrder(models.Model):
    _inherit = 'fsm.order'

    vehicle_id = fields.Many2one('fsm.vehicle',
                                 string='Vehicle')

    @api.multi
    def write(self, vals):
        res = super().write(vals)
        for order_id in self:
            if vals.get('vehicle_id', False):
                vehicle_id = self.env['fsm.vehicle'].browse(vals.get('vehicle_id'))
                if vehicle_id.inventory_location_id:
                    for sr_id in order.stock_request_ids:
                        if sr_id.request_stage in ['draft', 'submitted']: 
                            for move_id in sr_id.move_ids:
                                for move_line_id in move_id.move_line_ids:
                                    # Replace the "Vehicle / Storage" location on the stock move lines
        return res

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if vals.get('vehicle_id', False):
            vehicle_id = self.env['fsm.vehicle'].browse(vals.get('vehicle_id'))
            if vehicle_id.inventory_location_id:
                for sr_id in self.stock_request_ids:
                    if sr_id.request_stage in ['draft', 'submitted']: 
                        for move_id in sr_id.move_ids:
                            for move_line_id in move_id.move_line_ids:
                                # Replace the "Vehicle / Storage" location on the stock move lines
        return res

    @api.depends('fsm_route_id', 'person_id')
    def onchange_vehicle_id(self):
        if self.fsm_route_id:
            if self.fsm_route_id.vehicle_id:
                self.vehicle_id = self.fsm_route_id.vehicle_id
        elif self.person_id:
            if self.person_id.vehicle_id:
                self.vehicle_id = self.fsm_route_id.vehicle_id
