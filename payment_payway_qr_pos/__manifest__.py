{
    'name': 'POS Payway QR',
    'countries': ['KH'],
    'version': '1.0',
    'summary': 'POS payment module for Payway QR payments.',
    'author': 'ABA Bank',
    'category': 'Accounting/Payment',
    'depends': ['point_of_sale', 'payment_payway_qr_base'],
    'data': [
        'views/payment_provider_views.xml',
        # 'data/payment_provider_data.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'payment_payway_qr_pos/static/src/**/*',
        ],
    },
}
