# TODO: Consts should be sets ideally
# FIX: Store list of constant in set.
# For hash keys, cannot be converted as order matters.

PAYMENT_METHODS_MAPPING = {
    'card': 'cards',
    # TODO: Redundant?
    'abapay_khqr': 'abapay_khqr',
    'wechat_pay': 'wechat',
    'alipay': 'alipay',
}

# TODO: Keep only relevant ones. Use .get() when fetching from set.
PAYWAY_PAYMENT_METHODS_MAPPING = {
    'visa': 'visa',
    'mastercard': 'mc',
    'unionpay': 'cup',
    'jcb': 'jcb',
    'alipay': 'alipay',
    'wechat_pay': 'wechat',
}

DEFAULT_PAYMENT_METHODS_CODES = {
    'card',
    'abapay_khqr',
    'wechat_pay',
    'alipay',

    # Brand payment methods.
    'visa',
    'mastercard',
    'unionpay',
    'jcb',
}

PURCHASE_PAYMENT_SECURE_HASH_KEYS = [
    'req_time',
    'merchant_id',
    'tran_id',
    'amount',
    'firstname',
    'lastname',
    'email',
    'phone',
    'type',
    'payment_option',
    'return_url',
    'continue_success_url',
    'currency',
    'lifetime',
    'skip_success_page',
]

SUPPORTED_CURRENCIES = {
    'KHR',
    'USD',
}

CURRENCY_DECIMALS = {
    'KHR': 0,
    'USD': 2,
}

WEB_HOOK_PATH = {
    'webhook': '/payment/payway/webhook',
    'poll': '/payment/payway/status/poll',
}

STATUS_MAPPING = {
    'APPROVED': 'APPROVED',
    'PRE-AUTH': 'PRE-AUTH',
    'REFUNDED': 'REFUNDED',
    'PENDING': 'PENDING',
    'CANCELLED': 'CANCELLED',
}

BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
