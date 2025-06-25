{
    'name': 'Account Payway Payment QR Base',
    'countries': ['KH'],
    'version': '1.0',
    'category': 'Accounting/Payment',
    'summary': 'Base module for integrating Payway QR payments.',
    'description': """
        This module provides the core functionalities for interacting with Payway
        QR payment API, including configuration and QR generation logic.
    """,
    'author': 'ABA Bank',
    'depends': [
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'views/res_bank.xml',
    ],
    'license': 'LGPL-3',
}
