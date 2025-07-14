{
    'name': 'Payway Payment QR for POS',
    'countries': ['KH'],
    'version': '1.0',
    'summary': 'POS payment module for Payway QR payments.',
    'author': 'ABA Bank',
    'category': 'Point of Sale',
    'depends': [
        'point_of_sale',
        'account_payway_qr_base',
    ],
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'payment_payway_qr_pos/static/src/app/**/*',
        ],
        'point_of_sale.customer_display_assets': [
            'payment_payway_qr_pos/static/src/customer_display/**/*',
        ],
    },
    'installable': True,
}
