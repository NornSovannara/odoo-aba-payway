{
    'name': 'Payway Payment QR for POS',
    'countries': ['KH'],
    'version': '1.0',
    'summary': 'POS payment module for Payway QR payments.',
    'author': 'ABA Bank',
    'category': 'Point of Sale',
    'depends': [
        'point_of_sale',
        # 'payment_payway_qr_base',
        'account_payway_qr_base',
    ],
    'data': [
        # 'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'payment_payway_qr_pos/static/src/js/pos_store.js',
            'payment_payway_qr_pos/static/src/js/qr_code_popup.js',
        ],
    },
    'installable': True,
}
