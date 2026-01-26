import json
import time
import base64

from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo import _, models, fields, api

from odoo.addons.payment_aba_payway import const

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('aba_payway', "ABA PayWay")], ondelete={'aba_payway': 'set default'}
    )

    @api.depends('code')
    def _compute_view_configuration_fields(self):        
        super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.code == 'aba_payway').update({
            'require_currency': True,
        })

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'aba_payway').update({
            'support_refund': 'partial',
            'support_manual_capture': 'full_only',
        })

    # ==== CONSTRAINT METHODS ===#
    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'aba_payway':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _payway_get_api_cred(self):
        """Return the URL of the API corresponding to the selected payway environment.
        API cred is configured on the bank account module.

        :return: (API URL, Merchant ID, API Key).
        :rtype: (str, str, str)
        """
        self.ensure_one()
        return self.journal_id.bank_account_id._payway_get_api_cred()
    
    def _payway_calculate_payment_secure_hash(
            self, 
            api_key: str, 
            payload: dict, 
            secure_hash_keys: list = const.PURCHASE_PAYMENT_SECURE_HASH_KEYS
        ):
        
        self.ensure_one()
        return self.journal_id.bank_account_id._payway_calculate_payment_secure_hash(api_key, payload, secure_hash_keys)

    def _payway_api_check_transaction(self, tran_id: str):
        self.ensure_one()
        return self.journal_id.bank_account_id._payway_api_check_transaction(tran_id)

    def _payway_api_get_transaction_detail(self, tran_id: str):
        self.ensure_one()
        return self.journal_id.bank_account_id._payway_api_get_transaction_detail(tran_id)

    def _payway_api_refund_transaction(self, merchant_auth: str):
        self.ensure_one()
        return self.journal_id.bank_account_id._payway_api_refund_transaction(merchant_auth)

    def _payway_api_void_transaction(self, merchant_auth: str):
        self.ensure_one()
        return self.journal_id.bank_account_id._payway_api_void_transaction(merchant_auth)
    
    def _payway_api_capture_transaction(self, merchant_auth: str):
        self.ensure_one()
        return self.journal_id.bank_account_id._payway_api_capture_transaction(merchant_auth)

    def _payway_calculate_webhook_secure_hash(self, notification_data):
        self.ensure_one()

        _, _, api_key, _ = self._payway_get_api_cred()
        return self.journal_id.bank_account_id._payway_calculate_webhook_secure_hash(api_key, notification_data)

    def _payway_calculate_merchant_auth(self, public_key_pem: str, payload: dict):

        self.ensure_one()
        public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        data = json.dumps(payload).encode("utf-8")

        encrypted = bytearray()
        for i in range(0, len(data), 117):
            chunk = data[i : i + 117]
            encrypted.extend(public_key.encrypt(chunk, padding.PKCS1v15()))

        return base64.b64encode(bytes(encrypted)).decode("utf-8")

    def _compute_transaction_suffix(self):
        """Convert timestamp into base62, for suffix transaction reference.

        :rtype: str
        """        

        def to_base62(n: int) -> str:
            if n == 0:
                return const.BASE62_ALPHABET[0]
            
            base62 = []
            while n > 0:
                n, r = divmod(n, 62)
                base62.append(const.BASE62_ALPHABET[r])
            
            return ''.join(reversed(base62))
        
        timestamp = int(time.time())
        encoded = to_base62(timestamp)
        return encoded
    

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'aba_payway':
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES
