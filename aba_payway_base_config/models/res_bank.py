import hashlib
import hmac
import base64
import json
from datetime import datetime
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from odoo import _, api, fields, models
from odoo.addons.aba_payway_base_config import const
from odoo.addons.payment import utils as payment_utils
from odoo.exceptions import ValidationError

MAX_RETRY = 2

# TODO: Consider using Retry from urllib3 for a more standard implementation
# FIX: use urlib3 Retry
def _make_payway_api_request(base_url: str, endpoint: str, payload: dict):
    url = urljoin(base_url, endpoint)

    retry_strategy = Retry(
        total=MAX_RETRY,
        backoff_factor=1,
        status_forcelist=[400, 401, 403, 404, 405, 429, 500, 502, 503, 504],
        allowed_methods=["POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)

    try:
        response = session.post(
            url, json=payload, timeout=30, verify=True
        )
        return response.json()
    except (requests.RequestException, ValueError) as err:
        raise ValidationError(
            _("Could not establish a connection to PayWay API. Error: %s", err)
        )


class ResBank(models.Model):
    _inherit = "res.partner.bank"

    # TODO: Can use the same fields for both prod and sandbox.
    # COMMENT: As per checkout with our PO,
    # We decide th keep seperate fields for both env
    # so, when user switch env, they dont have to re-enter cred

    # TODO: Ideally store credentials under payment.provider
    
    # TODO Modify _payway_get_api_cred() to differentiate between prod and sandbox
    # FIX: differentiate cred field between prod and sandbox,
    # _payway_get_api_cred() also return base on enviroment

    production_payway_merchant_id = fields.Char(
        string='Merchant ID',
        help="Enter your production PayWay Merchant ID. You'll receive this by email after obtaining a Go Live approval from ABA PayWay.",
    )
    production_payway_key = fields.Char(
        string='API Key',
        help="Enter your production PayWay API Key. You'll receive this by email after obtaining a Go Live approval from ABA PayWay.",
        groups='base.group_system',
    )
    production_rsa_public_key = fields.Text(
        string='RSA Public Key',
        help="Enter your production PayWay RSA Public Key. You'll receive this by email after obtaining a Go Live approval from ABA PayWay.",
        groups='base.group_system',
    )

    sandbox_payway_merchant_id = fields.Char(
        string='Merchant ID',
        help='Enter your unique PayWay Merchant ID. You can find it in the email registered for your PayWay Sandbox account.',
    )
    sandbox_payway_key = fields.Char(
        string='API Key',
        help='Enter your unique PayWay API Key. You can find it in the email registered for your PayWay Sandbox account.',
        groups='base.group_system',
    )
    sandbox_rsa_public_key = fields.Text(
        string='RSA Public Key',
        help='Enter your unique PayWay RSA Public Key. You can find it in the email registered for your PayWay Sandbox account.',
        groups='base.group_system',
    )

    payway_environment = fields.Selection(
        [('disable', 'Disable'), ('production', 'Production'), ('sandbox', 'Sandbox')],
        string='Environment',
        default='disable',
        required=True,
        help='Switch between Sandbox and Production payment environments for ABA PayWay.',
    )

    digital_qr_lifetime = fields.Integer(
        string='QR on screen expire time (minute)',
        default=3,
        required=True,
    )

    bill_qr_lifetime = fields.Integer(
        string='QR on Bill expire time (Minute)',
        default=10,
        required=True,        
    )


    @api.constrains('digital_qr_lifetime', 'bill_qr_lifetime')
    def _check_qr_lifetimes(self):
        for record in self:
            if not isinstance(record.digital_qr_lifetime, int) or record.digital_qr_lifetime < 1:
                raise ValidationError("QR on screen expire time must be an integer and at least 1 minute.")
            if not isinstance(record.bill_qr_lifetime, int) or record.bill_qr_lifetime < 1:
                raise ValidationError("QR on Bill expire time must be an integer and at least 1 minute.")
            
            if record.digital_qr_lifetime > 43200 or record.bill_qr_lifetime > 43200:
                raise ValidationError("QR expire time must not be greater than 30 Days.")

    @api.model
    def _get_available_qr_methods(self):
        """Extend the base list of QR methods."""
        res = super()._get_available_qr_methods()
        res.append(('abapay_khqr', _("ABA KHQR"), 10))
        res.append(('wechat', _("WeChat Pay"), 10))
        res.append(('alipay', _("Alipay"), 10))
        return res

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        # Raise error msg

        if self.sudo().payway_environment == 'disable':
            return _("ABA PayWay is currently disabled. Please select an environment to proceed.")
        
        if currency.name not in ['USD', 'KHR']:
            return _("This payment method only supports transactions in USD or KHR currency.\nTo continue, please update your store currency and try again.")

        if self.sudo().payway_environment == 'production':
            if not self.sudo().production_payway_merchant_id:
                return _("For Production environment, the 'PayWay Merchant ID' is required.")
            if not self.sudo().production_payway_key:
                return _("For Production environment, the 'PayWay API Key' is required.")

        elif self.sudo().payway_environment == 'sandbox':
            if not self.sudo().sandbox_payway_merchant_id:
                return _("For Sandbox environment, the 'PayWay Merchant ID' is required.")
            if not self.sudo().sandbox_payway_key:
                return _("For Sandbox environment, the 'PayWay API Key' is required.")

        return super()._get_error_messages_for_qr(qr_method, debtor_partner, currency)
    

    def _get_qr_vals(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        
        if qr_method in const.PAYMENT_METHODS_CODES:

            model = self._context.get('model')
            qr_type = self._context.get('qr_type')
            qr_tran_id = self._context.get('qr_tran_id') if self._context.get('qr_tran_id') else ""

            api_url, merchant_id, api_key, _ = self._payway_get_api_cred()
            self._payway_api_close_transaction(qr_tran_id)

            base_odoo_url:str = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_odoo_url = (
                base_odoo_url.replace('http://', 'https://', 1)
                if base_odoo_url and base_odoo_url.startswith('http://') else base_odoo_url
            )
            webhook_url = urljoin(base_odoo_url, const.WEB_HOOK_PATH['pos']) if model == 'pos.order' else ''
            
            payload = {
                'req_time': datetime.now().strftime("%Y%m%d%H%M%S"),
                'merchant_id': merchant_id,
                'tran_id': qr_tran_id,                
                'email': self.partner_id.email,
                'phone': self.partner_id.phone,
                'amount': amount,
                'payment_option': qr_method,
                'currency': currency.name.upper(),
                'lifetime': (
                    self.bill_qr_lifetime 
                    if qr_type == const.POS_ORDER_QR_TYPE['bill'] else 
                    self.digital_qr_lifetime
                ),
                'qr_image_template': (
                    'template2' if model == 'pos.order' and 
                    qr_type == const.POS_ORDER_QR_TYPE['bill'] else 'template1_color'
                ),
                'callback_url': base64.b64encode(webhook_url.encode('utf-8')).decode(
                    'utf-8'
                ),
            }

            # TODO: QR_PAYMENT_SECURE_HASH_KEYS doesn't exist?
            payload.update(
                {'hash': self._payway_calculate_payment_secure_hash(api_key, payload, const.QR_PAYMENT_SECURE_HASH_KEYS)}
            )

            return api_url, payload

        return super()._get_qr_vals(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    def _get_qr_code_generation_params(
        self,
        qr_method,
        amount,
        currency,
        debtor_partner,
        free_communication,
        structured_communication,
    ):
        
        if qr_method in const.PAYMENT_METHODS_CODES:
            
            api_url, payload = self._get_qr_vals(
                qr_method,
                amount,
                currency,
                debtor_partner,
                free_communication,
                structured_communication,
            )
        
            response = _make_payway_api_request(
                api_url, '/api/payment-gateway/v1/payments/generate-qr', payload
            )

            if str(response['status']['code']) != '0':
                # Payway return error
                raise ValidationError(response['status']['message'])

            return {
                'barcode_type': 'QR',
                'width': 150,
                'height': 150,
                'value': response['qrString'],
            }

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
        
        return super()._get_qr_code_base64(
            qr_method,
            amount,
            currency,
            debtor_partner,
            free_communication,
            structured_communication,
        )

    def _payway_api_close_transaction(self, qr_tran_id: str):
        """Close payway transaction.

        :return: transaction id.
        :rtype: response dict
        """

        api_url, merchant_id, api_key, _ = self._payway_get_api_cred()
        payload = {
            'req_time': datetime.now().strftime("%Y%m%d%H%M%S"),
            'merchant_id': merchant_id,
            'tran_id': qr_tran_id,
        }
        payload.update(
            {'hash': self._payway_calculate_payment_secure_hash(api_key, payload, const.CHECK_TXN_SECURE_HASH_KEYS)}
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
    

    def _payway_api_check_transaction(self, qr_tran_id: str):
        """Check payway transaction.

        :return: transaction id.
        :rtype: response dict
        """
        api_url, merchant_id, api_key, _ = self._payway_get_api_cred()
        payload = {
            'req_time': datetime.now().strftime("%Y%m%d%H%M%S"),
            'merchant_id': merchant_id,
            'tran_id': qr_tran_id,
        }
        payload.update(
            {'hash': self._payway_calculate_payment_secure_hash(api_key, payload, const.CHECK_TXN_SECURE_HASH_KEYS)}
        )
        response = _make_payway_api_request(
            api_url, '/api/payment-gateway/v1/payments/check-transaction-2', payload
        )

        if str(response['status']['code']) == '00':
            return response

        raise ValidationError(response['status']['message'])


    def _payway_api_get_transaction_detail(self, qr_tran_id: str):
        """Get payway transaction detail.

        :return: transaction id.
        :rtype: reponse dict
        """
        api_url, merchant_id, api_key, _ = self._payway_get_api_cred()
        payload = {
            'req_time': datetime.now().strftime("%Y%m%d%H%M%S"),
            'merchant_id': merchant_id,
            'tran_id': qr_tran_id,
        }
        payload.update(
            {'hash': self._payway_calculate_payment_secure_hash(api_key, payload, const.CHECK_TXN_SECURE_HASH_KEYS)}
        )

        response = _make_payway_api_request(
            api_url, '/api/payment-gateway/v1/payments/transaction-detail', payload
        )

        if str(response['status']['code']) == '00':
            return response

        raise ValidationError(response['status']['message'])

    def _payway_api_refund_transaction(self, merchant_auth: str):
        """Request refund transaction.

        :return: transaction id.
        :rtype: reponse dict
        """
        api_url, merchant_id, api_key, _ = self._payway_get_api_cred()
        req_time = datetime.now().strftime('%Y%m%d%H%M%S')

        payload = {
            "request_time": req_time,
            "merchant_id": merchant_id,
            "merchant_auth": merchant_auth,
        }
        payload.update(
            {'hash': self._payway_calculate_payment_secure_hash(api_key, payload, const.REFUND_TXN_SECURE_HASH_KEYS)}
        )

        response = _make_payway_api_request(
            api_url, '/api/merchant-portal/merchant-access/online-transaction/refund', payload
        )

        if str(response['status']['code']) == '00':
            return response

        raise ValidationError(response['status']['message'])

    def _payway_api_void_transaction(self, merchant_auth: str):
        api_url, merchant_id, api_key, _ = self._payway_get_api_cred()
        req_time = datetime.now().strftime('%Y%m%d%H%M%S')

        payload = {
            "merchant_id": merchant_id,
            "merchant_auth": merchant_auth,
            "request_time": req_time,
        }

        payload.update(
            {'hash': self._payway_calculate_payment_secure_hash(api_key, payload, const.VOID_TXN_SECURE_HASH_KEYS)}
        )

        response = _make_payway_api_request(
            api_url, '/api/merchant-portal/merchant-access/online-transaction/pre-auth-cancellation', payload
        )

        if str(response['status']['code']) == '00':
            return response

        raise ValidationError(response['status']['message'])

    def _payway_api_capture_transaction(self, merchant_auth: str):
        api_url, merchant_id, api_key, _ = self._payway_get_api_cred()
        req_time = datetime.now().strftime('%Y%m%d%H%M%S')

        payload = {
            "merchant_auth": merchant_auth,
            "request_time": req_time,
            "merchant_id": merchant_id,
        }
        payload.update(
            {'hash': self._payway_calculate_payment_secure_hash(api_key, payload, const.CAPTURE_TXN_SECURE_HASH_KEYS)}
        )

        response = _make_payway_api_request(
            api_url, '/api/merchant-portal/merchant-access/online-transaction/pre-auth-completion', payload
        )

        if str(response['status']['code']) == '00':
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
                self.production_payway_key,
                self.production_rsa_public_key,
            )
        elif self.payway_environment == 'sandbox':
            api_url = const.API_URLS['sandbox']
            return (
                api_url,
                self.sandbox_payway_merchant_id,
                self.sandbox_payway_key,
                self.sandbox_rsa_public_key,
            )

    def _payway_calculate_payment_secure_hash(self, api_key: str, payload: dict, secure_hash_keys: list):
        """Compute the secure hash for the provided data according to the PayWay documentation.

        :param dict data: The data to hash.
        :return: The calculated hash.
        :rtype: str
        """

        data_to_sign = [str(payload.get(k, '')) for k in secure_hash_keys]
        signing_string = ''.join(data_to_sign)
        hmac_hash = hmac.new(
            api_key.encode(), signing_string.encode(), hashlib.sha512
        ).digest()
        base64_encoded = base64.b64encode(hmac_hash).decode()
        return base64_encoded


    def _payway_calculate_webhook_secure_hash(self, api_key: str, payload: dict):
        """Compute the secure hash for verifying webhook notifications from Payway.

        :return: The calculated hash.
        :rtype: str
        """

        data_to_sign = sorted(payload.keys())
        signing_string = ''.join([str(payload.get(k, '')) for k in data_to_sign])
        hmac_hash = hmac.new(
            api_key.encode(), signing_string.encode(), hashlib.sha512
        ).digest()
        base64_encoded = base64.b64encode(hmac_hash).decode()
        return base64_encoded
