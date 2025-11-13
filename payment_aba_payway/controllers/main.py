import logging
import pprint

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

from odoo.addons.payment_aba_payway import const

_logger = logging.getLogger(__name__)


class PayWayController(http.Controller):
    _webhook_url = const.WEB_HOOK_PATH['webhook']
    _poll_status_url = const.WEB_HOOK_PATH['poll']

    MONITORED_TX_ID_KEY = '__payment_monitored_tx_id__'

    @http.route(_webhook_url, type='json', auth='public', methods=['POST'], csrf=False)
    def payway_webhook(self):
        try:
            data = request.get_json_data()
            _logger.info(
                "Notification received from PayWay with data:\n%s", pprint.pformat(data)
            )

            tx_sudo = (
                request.env['payment.transaction']
                .sudo()
                ._get_tx_from_notification_data('aba_payway', data)
            )

            tx_sudo._handle_notification_data('aba_payway', data)

        except ValidationError:
            _logger.exception(
                "Unable to handle the notification data; skipping to acknowledge.",
                exc_info=True,
            )

    @http.route(_poll_status_url, type='json', auth='public')
    def payway_poll_check_transaction(self, **_kwargs):
        """Fetch the payway transaction and verify its status.
        In case webhook notification is not received, this is the fallback method.

        :return: The post-processing values of the transaction.
        :rtype: dict
        """
        # We only poll the payment status if a payment was found, so the transaction should exist.
        monitored_tx = self._get_monitored_transaction()

        if monitored_tx and monitored_tx.provider_code == 'aba_payway':
            try:
                data = {
                    'tran_id': monitored_tx.reference,
                }

                tx_sudo = (
                    request.env['payment.transaction']
                    .sudo()
                    ._get_tx_from_notification_data('aba_payway', data)
                )
                tx_sudo._handle_notification_data('aba_payway', data)

            except ValidationError:
                _logger.exception(
                    "Unable to handle the verify Payway transaction.", exc_info=True
                )

        return {
            'provider_code': monitored_tx.provider_code,
            'state': monitored_tx.state,
        }

    @staticmethod
    def _verify_notification_signature(notification_data, tx_sudo):
        """Check that the received signature matches the expected one.

        :param dict notification_data: The notification data
        :param recordset tx_sudo: The sudoed transaction referenced by the notification data, as a
                   `payment.transaction` record
        :return: None
        :raise: :class:`werkzeug.exceptions.Forbidden` if the signatures don't match
        """

        pass

    def _get_monitored_transaction(self):
        """Retrieve the user's last transaction from the session (the transaction being monitored).

        :return: the user's last transaction
        :rtype: payment.transaction
        """
        return (
            request.env['payment.transaction']
            .sudo()
            .browse(request.session.get(self.MONITORED_TX_ID_KEY))
            .exists()
        )
