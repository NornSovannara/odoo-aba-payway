# TODO: Consts should be sets ideally
# FIX: Store list of constant in set.
PAYMENT_METHODS_CODES = {
    'abapay_khqr',
    'wechat',
    'alipay',
}

# TODO: Redundant?
# COMMENT: Keep for explicitness.
PAYMENT_METHODS_MAPPING = {
    'abapay_khqr': 'abapay_khqr',
    'wechat': 'wechat',
    'alipay': 'alipay',
}

API_URLS = {
    'production': 'https://checkout.payway.com.kh',
    'sandbox': 'https://checkout-sandbox.payway.com.kh',
}

SUPPORTED_CURRENCIES = {
    'KHR',
    'USD',
}

CURRENCY_DECIMALS = {
    'KHR': 0,
    'USD': 2,
}

QR_PAYMENT_SECURE_HASH_KEYS = [
    'req_time',
    'merchant_id',
    'tran_id',
    'amount',
    'items',
    'first_name',
    'last_name',
    'email',
    'phone',
    'purchase_type',
    'payment_option',
    'callback_url',
    'return_deeplink',
    'currency',
    'custom_fields',
    'return_params',
    'payout',
    'lifetime',
    'qr_image_template',
]

CHECK_TXN_SECURE_HASH_KEYS = ['req_time', 'merchant_id', 'tran_id']
REFUND_TXN_SECURE_HASH_KEYS = ['request_time', 'merchant_id', 'merchant_auth']

POS_ORDER_QR_TYPE = {
    'screen': 'screen',
    'bill': 'bill',
}

WEB_HOOK_PATH = {
    'pos': '/pos/payway/webhook',
}


QR_METHOD_IMAGE_MAP = {
    'abapay_khqr': 'aba_khqr.png',
    'wechat': 'wechat.png',
    'alipay': 'alipay.png',
}

QR_METHOD_NAME_MAP = {
    'abapay_khqr': 'ABA KHQR',
    'wechat': 'WeChat Pay',
    'alipay': 'Alipay',
}
