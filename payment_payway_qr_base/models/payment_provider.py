import hashlib
import hmac
import base64
from typing import Dict
from odoo import _, api, fields, models
from odoo.addons.payment_payway_qr_base import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('payway', "Payway")], ondelete={'payway': 'set default'}
    )

    production_payway_merchant_id = fields.Char(
        string='PayWay Merchant ID',
        help='The Merchant ID solely used to identify your PayWay account.',
    )
    production_payway_public_key = fields.Char(
        string='PayWay public key',
        groups='base.group_system',
    )

    sandbox_payway_merchant_id = fields.Char(
        string='Sandbox PayWay Merchant ID',
        help='The Merchant ID solely used to identify your PayWay account.',
    )
    sandbox_payway_public_key = fields.Char(
        string='Sandbox PayWay public key',
        groups='base.group_system',
    )

    # === BUSINESS METHODS ===
    def _payway_get_api_cred(self):
        """Return the URL of the API corresponding to the provider's state.

        :return: The API URL.
        :rtype: str
        """
        self.ensure_one()
        if self.state == 'enabled':
            api_url = const.API_URLS['production']
            return (
                api_url,
                self.production_payway_merchant_id,
                self.production_payway_public_key,
            )
        else:
            api_url = const.API_URLS['sandbox']
            return (
                api_url,
                self.sandbox_payway_merchant_id,
                self.sandbox_payway_public_key,
            )

    def _payway_calculate_payment_secure_hash(self, api_key: str, data: Dict):
        """Compute the secure hash for the provided data according to the PayWay documentation.

        :param dict data: The data to hash.
        :return: The calculated hash.
        :rtype: str
        """
        secure_hash_keys = const.PAYMENT_SECURE_HASH_KEYS
        data_to_sign = [str(data[k]) for k in secure_hash_keys]
        signing_string = ''.join(data_to_sign)
        hmac_hash = hmac.new(
            api_key.encode("utf-8"), signing_string.encode(), hashlib.sha512
        ).digest()
        base64_encoded = base64.b64encode(hmac_hash).decode()
        return base64_encoded
