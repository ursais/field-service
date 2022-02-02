# Copyright (C) 2018 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _


class FSMOrder(models.Model):
    _inherit = "fsm.order"

    invoice_lines = fields.Many2many(
        "account.move.line",
        "fsm_order_account_move_line_rel",
        "fsm_order_id",
        "account_move_line_id",
        string="Invoice Lines",
        copy=False,
    )

    invoice_ids = fields.Many2many(
        "account.move",
        string="Invoices",
        compute="_compute_get_invoiced",
        readonly=True,
        copy=False,
    )

    invoice_count = fields.Integer(
        string="Invoice Count",
        compute="_compute_get_invoiced",
        readonly=True,
        copy=False,
    )

    @api.depends("invoice_lines")
    def _compute_get_invoiced(self):
        for order in self:
            self._cr.execute("SELECT account_move_line_id FROM fsm_order_account_move_line_rel WHERE fsm_order_id = %s", tuple([order.id]))
            move_line_ids = [i[0] for i in self._cr.fetchall()]
            moves = False
            if move_line_ids:
                move_lines = self.env['account.move.line'].browse(move_line_ids)
                moves = move_lines.mapped("move_id")
            order.invoice_ids = moves
            if moves:
                order.invoice_count = len(moves)
            else:
                order.invoice_count = 0

    def action_view_invoices(self):
        action = self.env.ref("account.action_move_out_invoice_type").read()[0]
        invoices = self.mapped("invoice_ids")
        if len(invoices) > 1:
            action["domain"] = [("id", "in", invoices.ids)]
        elif invoices:
            action["views"] = [(self.env.ref("account.view_move_form").id, "form")]
            action["res_id"] = invoices.ids[0]
        return action
