# Copyright (C) 2019 Open Source Integrators
# Copyright (C) 2019 Serpent consulting Services
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FSMStage(models.Model):
    _inherit = "fsm.stage"

    stage_type = fields.Selection(
        selection_add=[("route", "Route")], ondelete={"route": "cascade"}
    )
