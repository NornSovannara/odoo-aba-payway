{
    'name': 'Payway Payment QR Base',
    'countries': ['KH'],
    'version': '1.0',
    'summary': 'Base module for integrating Payway QR payments.',
    'description': """
        This module provides the core functionalities for interacting with Payway
        QR payment API, including configuration and QR generation logic.
    """,
    'author': 'ABA Bank',
    'category': 'Accounting/Payment',
    'depends': [
        'payment',
        'account',
    ],
    'data': [
        'views/payment_provider_views.xml',
        'data/payment_provider_data.xml',
    ],
    'auto_install': ['payment'],
}
