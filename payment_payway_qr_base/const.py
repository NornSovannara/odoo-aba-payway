API_URLS = {
    'production': 'https://checkout.payway.com.kh',
    'sandbox': 'https://checkout-sandbox.payway.com.kh',
}


DEFAULT_PAYMENT_METHODS_CODES = [
    'abapay_khqr',
    'wechat',
    'alipay',
]

PAYMENT_METHODS_MAPPING = {
    'abapay_khqr': 'abapay_khqr',
    'wechat': 'wechat',
    'alipay': 'alipay',
}

PAYMENT_SECURE_HASH_KEYS = [
    'req_time',
    'merchant_id',
    'tran_id',
    'amount',
    'firstname',
    'lastname',
    'email',
    'currency',
    'payment_option',
    'lifetime',
    'qr_image_template',
]
