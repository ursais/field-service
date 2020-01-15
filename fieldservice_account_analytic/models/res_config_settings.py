# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    filter_location_by_contact = fields.Boolean(
        string='Filter Contacts with Location',
        related='company_id.filter_location_by_contact',
        readonly=False
    )
