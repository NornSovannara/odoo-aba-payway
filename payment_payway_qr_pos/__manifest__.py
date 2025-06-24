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
        # 'views/pos_order_receipt_view.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'payment_payway_qr_pos/static/src/**/*',
            # 'payment_payway_qr_pos/static/src/js/pos_order_receipt.js',
            # 'payment_payway_qr_pos/static/src/xml/pos_order_receipt.xml',
        ],
    },
    'installable': True,
}
