import hashlib
import hmac
import base64
import json
import logging
from datetime import datetime
from urllib.parse import urljoin
import requests


from odoo import _, api, fields, models
from odoo.addons.account_payway_qr_base import const
from odoo.exceptions import ValidationError

"""
Configuration API key
Set up payment method
Get API params
"""
_logger = logging.getLogger(__name__)

MAX_RETRY = 2


def _make_payway_api_request(base_url: str, endpoint: str, payload: dict):

    url = urljoin(base_url, endpoint)
    headers = {"Content-Type": "application/json"}

    # Retry 2 more time
    for attempt in range(MAX_RETRY + 1):
        try:
            response = requests.post(
                url, headers=headers, data=json.dumps(payload), verify=False
            )

            if response.status_code != 200:
                response.raise_for_status()

            return response.json()

        except requests.exceptions.HTTPError as err:
            # Handle HTTP Exception from API
            if attempt == MAX_RETRY:
                return response.json()

            continue

        except (requests.RequestException, ValueError) as err:
            if attempt == MAX_RETRY:
                raise ValidationError(
                    _("Could not establish a connection to PayWay API. Error: %s", err)
                )
            continue

    raise ValidationError(_("Could not establish a connection to PayWay API."))


class ResBank(models.Model):
    _inherit = "res.partner.bank"

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

    payway_environment = fields.Selection(
        [('production', 'Production'), ('sandbox', 'Sandbox')],
        string='PayWay Environment',
        default=const.PAYWAY_ENVIRONMENT['production'],
        help='Select the environment for PayWay integration.',
    )

    @api.model
    def _get_available_qr_methods(self):
        """Extend the base list of QR methods."""
        res = super()._get_available_qr_methods()
        res.append(('abapay_khqr', _("AbaPay KHQR"), 10))
        res.append(('wechat_pay', _("WeChat Pay"), 10))
        res.append(('alipay', _("Alipay"), 10))
        return res

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        # Raise error msg
        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)

    def _get_qr_code_generation_params(
        self,
        qr_method,
        amount,
        currency,
        debtor_partner,
        free_communication,
        structured_communication,
    ):

        return super()._get_qr_code_generation_params(
            qr_method,
            amount,
            currency,
            debtor_partner,
            free_communication,
            structured_communication,
        )

    def _get_qr_code_base64(
        self,
        qr_method,
        amount,
        currency,
        debtor_partner,
        free_communication,
        structured_communication,
    ):
        if qr_method in const.PAYMENT_METHODS_CODES:
            # Call API for generate base 64 here.

            model = self._context.get('model')
            model_id = self._context.get('model_id')
            qr_tran_id = self._context.get('qr_tran_id').split(" ")[-1]

            _logger.warning(
                (
                    f"My custom print {model}, {model_id}, {self.production_payway_merchant_id}, {self.production_payway_public_key}, {self.sandbox_payway_public_key}, {self.sandbox_payway_merchant_id} "
                    f"{qr_tran_id}"
                )
            )

            api_url, merchant_id, api_key = self._payway_get_api_cred()
            self._close_payway_transaction(qr_tran_id)

            payload = {
                'req_time': datetime.now().strftime("%Y%m%d%H%M%S"),
                'merchant_id': merchant_id,
                'tran_id': qr_tran_id,
                # 'first_name': self.partner_id.name.split()[0],
                # 'last_name': self.partner_id.name.split()[-1],
                'email': self.partner_id.email,
                'phone': self.partner_id.phone,
                'amount': amount,
                'payment_option': qr_method,
                'currency': currency.name.upper(),
                'lifetime': 3,
                'qr_image_template': 'template3_color',
            }
            payload.update(
                {'hash': self._payway_calculate_payment_secure_hash(api_key, payload)}
            )

            response = _make_payway_api_request(
                api_url, '/api/payment-gateway/v1/payments/generate-qr', payload
            )
            print(response)
            if str(response['status']['code']) != '0':
                # Payway return error
                raise ValidationError(response['status']['message'])

            return response['qrImage']

        return super()._get_qr_code_base64(
            qr_method,
            amount,
            currency,
            debtor_partner,
            free_communication,
            structured_communication,
        )

    # def build_qr_code_base64(
    #     self,
    #     amount,
    #     free_communication,
    #     structured_communication,
    #     currency,
    #     debtor_partner,
    #     qr_method=None,
    #     silent_errors=True,
    # ):

    #     if qr_method in const.PAYMENT_METHODS_CODES:
    #         pass

    #     return super().build_qr_code_base64(
    #         amount,
    #         free_communication,
    #         structured_communication,
    #         currency,
    #         debtor_partner,
    #         qr_method,
    #         silent_errors=silent_errors,
    #     )

    # === BUSINESS METHODS ===#

    def _close_payway_transaction(self, qr_tran_id: str):
        """Cloase payway transaction.

        :return: transaction id.
        :rtype: reponse dict
        """
        api_url, merchant_id, api_key = self._payway_get_api_cred()
        payload = {
            'req_time': datetime.now().strftime("%Y%m%d%H%M%S"),
            'merchant_id': merchant_id,
            'tran_id': qr_tran_id,
        }
        payload.update(
            {'hash': self._payway_calculate_check_txn_secure_hash(api_key, payload)}
        )
        response = _make_payway_api_request(
            api_url, '/api/payment-gateway/v1/payments/close-transaction', payload
        )

        if (
            str(response['status']['code']) == '00'
            or str(response['status']['code']) == '5'
        ):
            # Success or Transaction no found
            return response

        raise ValidationError(response['status']['message'])

    def _payway_get_api_cred(self):
        """Return the URL of the API corresponding to the selected payway environment.

        :return: (API URL, Merchant ID, API Key).
        :rtype: (str, str, str)
        """

        self.ensure_one()
        if self.payway_environment == 'production':
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

    def _payway_calculate_payment_secure_hash(self, api_key: str, payload: dict):
        """Compute the secure hash for the provided data according to the PayWay documentation.

        :param dict data: The data to hash.
        :return: The calculated hash.
        :rtype: str
        """

        secure_hash_keys = const.PAYMENT_SECURE_HASH_KEYS
        data_to_sign = [str(payload.get(k, '')) for k in secure_hash_keys]
        signing_string = ''.join(data_to_sign)
        hmac_hash = hmac.new(
            api_key.encode(), signing_string.encode(), hashlib.sha512
        ).digest()
        base64_encoded = base64.b64encode(hmac_hash).decode()
        return base64_encoded

    def _payway_calculate_check_txn_secure_hash(self, api_key: str, payload: dict):
        """Compute the secure hash for the provided data according to the PayWay documentation for checking transaction.

        :param dict data: The data to hash.
        :return: The calculated hash.
        :rtype: str
        """
        secure_hash_keys = const.CHECK_TXN_SECURE_HASH_KEYS
        data_to_sign = [str(payload[k]) for k in secure_hash_keys]
        signing_string = ''.join(data_to_sign)
        hmac_hash = hmac.new(
            api_key.encode(), signing_string.encode(), hashlib.sha512
        ).digest()
        base64_encoded = base64.b64encode(hmac_hash).decode()
        return base64_encoded
