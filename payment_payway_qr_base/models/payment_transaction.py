import json
from typing import Dict
from datetime import datetime
import requests

from odoo import _, api, models
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment_payway_qr_base import const


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_processing_values(self):
        self.ensure_one()

    def _get_specific_rendering_values(self, data: Dict):
        """Call Payway API to generate QR code

        :param dict data: The data .
        """
        res = super()._get_specific_rendering_values(data)
        if self.provider_code != 'payway':
            return res

        base_url = self.provider_id.get_base_url()
        api_url, merchant_id, payway_public_key = (
            self.provider_id._payway_get_api_cred()
        )
        partner_first_name, partner_last_name = payment_utils.split_partner_name(
            self.partner_name
        )

        payload = {
            'req_time': datetime.now().strftime("%Y%m%d%H%M%S"),
            'merchant_id': merchant_id,
            'tran_id': self.reference,
            'amount': self.amount,
            'firstname': partner_first_name,
            'lastname': partner_last_name,
            'email': self.partner_email,
            'currency': self.currency_id.name,
            'payment_option': const.PAYMENT_METHODS_MAPPING[
                self.payment_method_id.code
            ],
            'lifetime': 5,
            'qr_image_template': 'template1_color',
        }

        payload.update(
            {
                'hash': self.provider_id._payway_calculate_payment_secure_hash(
                    payway_public_key, payload
                )
            }
        )
        res.update(
            {
                'qr_api_url': api_url + "/api/payment-gateway/v1/payments/generate-qr",
                'qr_api_payload': payload,
            }
        )

        return res

    @api.model
    def _qr_payment_generate(self):
        """Call the API"""
        self.ensure_one()
        rendering_values = self._get_specific_rendering_values({})
        payway_qr_api_url = rendering_values['qr_api_url']
        headers = {"Content-Type": "application/json"}

        response = requests.post(
            payway_qr_api_url,
            headers=headers,
            data=json.dumps(rendering_values['qr_api_payload']),
        )
        data = response.json()

        return True, data['qrImage']
