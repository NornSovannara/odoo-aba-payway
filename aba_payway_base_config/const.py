# TODO: Consts should be sets ideally
API_URLS = {
    'production': 'https://checkout.payway.com.kh',
    'sandbox': 'https://checkout-sandbox.payway.com.kh',
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

PAYMENT_METHODS_CODES = [
    'abapay_khqr',
    'wechat',
    'alipay',
]

# TODO: Redundant?
PAYMENT_METHODS_MAPPING = {
    'abapay_khqr': 'abapay_khqr',
    'wechat': 'wechat',
    'alipay': 'alipay',
}

# TODO: Redundant?
POS_ORDER_QR_TYPE = {
    'screen': 'screen',
    'bill': 'bill',
}

WEB_HOOK_PATH = {
    'pos': '/pos/payway/webhook',
}

REFUND_TXN_SECURE_HASH_KEYS = ['request_time', 'merchant_id', 'merchant_auth']

VOID_TXN_SECURE_HASH_KEYS = ['merchant_id', 'merchant_auth', 'request_time']

CAPTURE_TXN_SECURE_HASH_KEYS = ["merchant_auth", "request_time", "merchant_id"]