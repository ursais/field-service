# Copyright (C) 2018 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class FSMOrder(models.Model):
    _inherit = 'fsm.order'

    invoice_ids = fields.Many2many(
        'account.invoice', 'fsm_order_account_invoice_rel',
        'fsm_order_id', 'invoice_id', string='Invoices/Bills')
    invoice_count = fields.Integer(
        string='Invoice Count',
        compute='_compute_account_invoice_count', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Contact',
                                  domain=[('customer', '=', True)],
                                  change_default=True,
                                  index=True,
                                  track_visibility='always')

    @api.onchange('location_id', 'customer_id')
    def _onchange_location_id_customer_account(self):
        if self.env.user.company_id.fsm_filter_location_by_contact:
            if self.location_id:
                return {'domain': {'customer_id': [('service_location_id', '=',
                                                    self.location_id.id)]}}
            else:
                return {'domain': {'customer_id': [],
                                   'location_id': []}}
        else:
            if self.customer_id:
                return {'domain': {'location_id': [('partner_id', '=',
                                                    self.customer_id.id)]}}
            else:
                return {'domain': {'location_id': [],
                                   'customer_id': []}}

    @api.onchange('customer_id')
    def _onchange_customer_id_location(self):
        if self.customer_id:
            self.location_id = self.customer_id.service_location_id

    @api.multi
    def write(self, vals):
        for order in self:
            if 'customer_id' not in vals and order.customer_id is False:
                vals.update({'customer_id': order.location_id.customer_id.id})
            return super(FSMOrder, self).write(vals)

    @api.depends('invoice_ids')
    def _compute_account_invoice_count(self):
        for order in self:
            order.invoice_count = len(order.invoice_ids)

    @api.multi
    def action_view_invoices(self):
        action = self.env.ref(
            'account.action_invoice_tree').read()[0]
        if self.invoice_count > 1:
            action['domain'] = [('id', 'in', self.invoice_ids.ids)]
        elif self.invoice_ids:
            action['views'] = \
                [(self.env.ref('account.invoice_form').id, 'form')]
            action['res_id'] = self.invoice_ids[0].id
        return action
