# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class AccountBatchPaymentLine(models.Model):
    _name = 'account.batch.payment.line'
    _description = 'Batch Payment Line'

    batch_payment_id = fields.Many2one(
        'account.batch.payment',
        string='Batch Payment',
        required=True,
        ondelete='cascade'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer/Vendor',
        required=True
    )
    amount = fields.Monetary(
        string='Amount',
        required=True
    )
    currency_id = fields.Many2one(
        related='batch_payment_id.currency_id',
        store=True
    )
    ref = fields.Char(
        string='Reference',
        help="Memo/Reference for the payment"
    )
    payment_id = fields.Many2one(
        'account.payment',
        string='Created Payment',
        readonly=True,
        copy=False
    )
    state = fields.Selection(
        related='payment_id.state',
        string='Status',
        store=True,
        readonly=True
    )
    batch_type = fields.Selection(
        related='batch_payment_id.batch_type',
        store=True,
        readonly=True
    )

    # The @api.constrains ('_check_partner_type') method
    # has been removed to allow creating payments
    # regardless of partner type, as requested.