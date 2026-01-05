# batch_payment/models/account_batch_payment.py
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class AccountBatchPayment(models.Model):
    _name = 'account.batch.payment'
    _description = 'Batch Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    date = fields.Date(
        string='Batch Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Bank Journal',
        required=True,
        domain="[('type', 'in', ('bank', 'cash'))]",
        tracking=True,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    
    payment_ids = fields.One2many(
        'account.batch.payment.line', # Changed from account.payment
        'batch_payment_id',
        string='Payments',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    
    payment_method_id = fields.Many2one(
        'account.payment.method',
        string='Payment Method',
        required=True,
        tracking=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('payment_type', '=', batch_type)]"
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated') # Changed from sent/reconciled
    ], string='Status', default='draft', required=True, tracking=True, readonly=True)
    
    batch_type = fields.Selection([
        ('outbound', 'Vendor Payments'),
        ('inbound', 'Customer Payments')
    ], string='Type', required=True, 
       tracking=True, readonly=True,
       states={'draft': [('readonly', False)]})
    
    amount_total = fields.Monetary(
        string='Total Amount',
        compute='_compute_amount_total',
        store=True,
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        readonly=True,
        states={'draft': [('readonly', False)]}
    )
    
    payment_count = fields.Integer(
        string='Payment Count',
        compute='_compute_payment_count',
        store=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company
    )

    @api.depends('payment_ids')
    def _compute_payment_count(self):
        for batch in self:
            batch.payment_count = len(batch.payment_ids)

    @api.depends('payment_ids.amount')
    def _compute_amount_total(self):
        for batch in self:
            batch.amount_total = sum(batch.payment_ids.mapped('amount'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq_code = 'account.batch.payment.out' if vals.get('batch_type') == 'outbound' else 'account.batch.payment.in'
                vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or _('New')
        return super().create(vals_list)

    # _validate_payment_lines method removed as requested

    def action_validate_batch(self):
        """
        Validate the batch:
        1. Create individual payments for each line.
        2. Post them.
        3. Link them to the lines.
        4. Set state to 'validated'.
        """
        self.ensure_one()
        
        if not self.payment_ids:
            raise UserError(_('Please add at least one payment line to the batch.'))
        
        # Determine partner_type directly from batch_type, without validation
        partner_type = 'customer' if self.batch_type == 'inbound' else 'supplier'
        
        Payment = self.env['account.payment']
        payments_to_post = self.env['account.payment']
        
        for line in self.payment_ids.filtered(lambda l: not l.payment_id):
            if line.amount <= 0:
                raise UserError(_("Payment amount for partner '%s' must be positive.") % line.partner_id.name)

            payment_vals = {
                'date': self.date,
                'amount': line.amount,
                'payment_type': self.batch_type,
                'partner_id': line.partner_id.id,
                'partner_type': partner_type, # <-- This is forced now
                'ref': line.ref or self.name,
                'journal_id': self.journal_id.id,
                'currency_id': self.currency_id.id,
                'payment_method_id': self.payment_method_id.id,
            }
            
            payment = Payment.create(payment_vals)
            payments_to_post |= payment
            line.write({'payment_id': payment.id})
            
        # Post all created payments
        if payments_to_post:
            payments_to_post.action_post()
        
        self.write({'state': 'validated'})
        return True

    def action_draft(self):
        """
        Reset batch payment to draft:
        1. Cancel and delete all associated payments.
        2. Clear payment link from lines.
        3. Set batch state to 'draft'.
        """
        self.ensure_one()
        
        payments = self.payment_ids.mapped('payment_id')
        if payments:
            if any(p.state == 'reconciled' for p in payments):
                raise UserError(_('You cannot reset a batch that contains reconciled payments.'))
            
            payments.filtered(lambda p: p.state == 'posted').button_draft()
            payments.filtered(lambda p: p.state in ('draft', 'posted')).button_cancel()
            
            # Unlink payments
            payments.unlink()
            
        self.payment_ids.write({'payment_id': False})
        
        self.write({'state': 'draft'})
        return True

    def action_view_payments(self):
        """Open the list of payments created by this batch"""
        self.ensure_one()
        created_payment_ids = self.payment_ids.mapped('payment_id').ids
        
        action_context = {
            'default_payment_type': self.batch_type,
            'default_partner_type': 'customer' if self.batch_type == 'inbound' else 'supplier'
        }
        
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', created_payment_ids)],
            'context': action_context
        }
    
    def action_print_batch_payment(self):
        """Print batch payment report"""
        self.ensure_one()
        return self.env.ref('batch_payment.action_report_batch_payment').report_action(self)

    def unlink(self):
        """Prevent deletion of non-draft batch payments"""
        for batch in self:
            if batch.state != 'draft':
                raise UserError(_('You cannot delete a batch payment that is not in draft state.'))
        return super().unlink()