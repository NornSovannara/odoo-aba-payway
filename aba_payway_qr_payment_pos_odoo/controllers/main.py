import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden
from odoo import http
from odoo.http import request
from odoo.addons.aba_payway_qr_payment_pos_odoo import const

_logger = logging.getLogger(__name__)

class PayWayController(http.Controller):
    _webhook_url = '/pos/payway/webhook'

    @http.route(_webhook_url, type='json', auth='public', methods=['POST'], csrf=False)
    def payway_webhook(self):

        try:
            data = request.get_json_data()
            _logger.info("Notification received from PayWay with data:\n%s", pprint.pformat(data))        
            channel_name = 'pos.order.payment.payway.' + data['tran_id']
            
            # TODO: Verify webhook signature
            
            # PROBLEM: pos.payment does not exist before order completed
            # So, I cannot retreive by transaction_id
            # bank = request.env['pos.payment'].sudo().search([
            #     ('transaction_id', '=', data['tran_id']),
            # ], limit=1).payment_method_id.journal_id.bank_account_id

            # As a workaround, I will search for any payment method with qr code method and get bank account from it
            payment_method = request.env['pos.payment.method'].sudo().search([
                ('qr_code_method', 'in', list(const.PAYMENT_METHODS_CODES))
            ], limit=1)
            bank_account = payment_method.journal_id.bank_account_id

            received_signature = request.httprequest.headers.get('x-payway-hmac-sha512')
            self._verify_notification_signature(data, received_signature, bank_account)

            # Send notification from backend
            request.env['bus.bus'].sudo()._sendone(
                channel_name,
                'notification',
                {
                    **data,
                    "channel_name": channel_name
                },  
            )

        except Exception:
            _logger.exception("Unable to handle the webhook data.")

        return "OK"


    @staticmethod
    def _verify_notification_signature(notification_data, received_signature, bank_account):
        """ Check that the received signature matches the expected one.

        :param dict notification_data: The notification data
        :param recordset bank_account: `res.partner.bank` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """

        if not received_signature:
            _logger.warning("Received notification with missing signature.")
            raise Forbidden()
        
        _, _, api_key = bank_account._payway_get_api_cred()
        expected_signature = bank_account._payway_calculate_webhook_secure_hash(api_key, notification_data)
        if (
            expected_signature is None
            or not hmac.compare_digest(received_signature, expected_signature)
        ):
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden()