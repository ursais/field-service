# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    disable_split_invoicing = fields.Boolean(related="company_id.disable_split_invoicing", readonly=False)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        res['disable_split_invoicing'] = self.env['ir.config_parameter'].sudo().get_param('fieldservice_sale.disable_split_invoicing')

        return res

    @api.model
    def set_values(self):
        self.env['ir.config_parameter'].sudo().set_param('fieldservice_sale.disable_split_invoicing', self.disable_split_invoicing)

        super(ResConfigSettings, self).set_values()
