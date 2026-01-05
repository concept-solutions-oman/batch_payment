{
    'name': 'Batch Payment',
    'version': '17.0.0.0.0',
    'category': 'Accounting',
    'summary': 'Create and post multiple payments from a single batch screen.',
    'description': """
        Batch Payment Module for Odoo 17 Community
        ===========================================
        
        This module allows users to create a batch payment to register multiple
        payments at once.
        
        Workflow:
        1. Create a new Batch Payment.
        2. Select the type (Vendor or Customer), Journal, Payment Method, and Date.
        3. In the 'Payments' tab, add lines for each payment (Partner, Amount, Reference).
        4. Click 'Validate'.
        5. The system will create and post one 'account.payment' record for each line.
        
        This simplifies entering many payments (e.g., from a bank file) 
        without having to create each one individually.
    """,
    'author': 'Concept Solutions',
    'website': 'https://www.csloman.com',
    'license': 'OPL-1',
    'depends': [
        'account'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/account_batch_payment_sequence.xml',
        'views/account_batch_payment_views.xml',
        'views/menu_views.xml',
        'reports/batch_payment_report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'price': 360.00,
    'currency': 'USD',
}