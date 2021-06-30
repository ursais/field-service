# -*- coding: utf-8 -*-


from odoo import fields, models, _

class ResCompany(models.Model):
    _inherit = "res.company"

    disable_split_invoicing = fields.Boolean(string="Disable Split Invoicing")
