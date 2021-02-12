# Copyright (C) 2021, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    fsm_filter_location_by_contact = fields.Boolean(
        string="Filter Contacts with Location",
        related="company_id.fsm_filter_location_by_contact",
        readonly=False,
    )
