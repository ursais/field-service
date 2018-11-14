# Copyright (C) 2018 - TODAY, Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FSMTerritory(models.Model):
    _name = 'fsm.territory'
    _description = 'Territory'

    name = fields.Char(string='Name')
    branch_id = fields.Many2one('fsm.branch', string='Branch')

    description = fields.Char(string='Description')
    fsm_person_id = fields.Many2one('fsm.person', string='Primary Assignment')
    terr_type = fields.Selection([('zip', 'Zip'), ('state', 'State'),
         ('country', 'Country')], 'Type')
    
    zip_codes = fields.Char(string='ZIP Codes')
    state_ids = fields.One2many('res.country.state',
         'sales_territory_id', string='State Names')
    country_ids = fields.One2many('res.country',
         'sales_territory_id', string='Country Names')
