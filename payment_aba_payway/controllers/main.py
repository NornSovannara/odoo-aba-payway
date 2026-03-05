import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden
from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


from odoo.addons.payment_aba_payway import const

_logger = logging.getLogger(__name__)

class PayWayController(http.Controller):
    _webhook_url =  const.WEB_HOOK_PATH['webhook']

    @http.route(_webhook_url, type='json', auth='public', methods=['POST'], csrf=False)
    def payway_webhook(self):
        try:
            data = request.get_json_data()
            _logger.info("Notification received from PayWay with data:\n%s", pprint.pformat(data))
            
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'aba_payway', data
            )

            received_signature = request.httprequest.headers.get('x-payway-hmac-sha512')
            self._verify_notification_signature(data, received_signature, tx_sudo)

            data.update(
                {
                    "payment_status": const.STATUS_MAPPING["PRE-AUTH"]
                    if tx_sudo.provider_id.capture_manually
                    else const.STATUS_MAPPING["APPROVED"],
                }
            )

            tx_sudo._handle_notification_data('aba_payway', data)

        except ValidationError:
            _logger.exception("Unable to handle the notification data; skipping to acknowledge.", exc_info=True)


    @staticmethod
    def _verify_notification_signature(notification_data, received_signature, tx_sudo):
        """ Check that the received signature matches the expected one.

        :param dict notification_data: The notification data
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                   `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """

        if not received_signature:
            _logger.warning("Received notification with missing signature.")
            raise Forbidden()
        
        expected_signature = tx_sudo.provider_id._payway_calculate_webhook_secure_hash(notification_data)
        if (
            expected_signature is None
            or not hmac.compare_digest(received_signature, expected_signature)
        ):
            _logger.warning("Received notification with invalid signature.")
            raise Forbidden()
