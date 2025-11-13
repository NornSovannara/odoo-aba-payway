from datetime import datetime
from urllib.parse import urljoin
import logging

from odoo.exceptions import UserError
from odoo import _, models, fields, api
from odoo.addons.payment import utils as payment_utils
from odoo.tools import float_round
from odoo.exceptions import ValidationError

from odoo.addons.payment_aba_payway import const

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """Override of payment to return ABA Payway specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """

        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'aba_payway':
            return res

        api_url, merchant_id, api_key = self.provider_id._payway_get_api_cred()

        req_time = datetime.now().strftime('%Y%m%d%H%M%S')
        partner_first_name, partner_last_name = payment_utils.split_partner_name(
            self.partner_name
        )
        payment_option = const.PAYMENT_METHODS_MAPPING[self.payment_method_id.code]

        # The amount is explicitly converted to a string to prevent a hash mismatch.
        # This avoids issues where JavaScript drops trailing zeros from numbers (e.g., 23.0 becomes 23),
        rounded_amount = str(
            float_round(
                processing_values.get('amount'),
                const.CURRENCY_DECIMALS.get(self.currency_id.name),
                rounding_method='DOWN',
            )
        )

        base_odoo_url: str = (
            self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        )
        webhook_url = urljoin(
            (
                base_odoo_url.replace('http://', 'https://', 1)
                if base_odoo_url and base_odoo_url.startswith('http://')
                else base_odoo_url
            ),
            const.WEB_HOOK_PATH['webhook'],
        )

        rendering_values = {
            'form_url': api_url + '/api/payment-gateway/v1/payments/purchase',
            # Use order reference as transaction id for payway, as this already has unique constraint.
            'tran_id': self.reference,
            'req_time': req_time,
            'lifetime': 3,
            'firstname': partner_first_name and partner_first_name[:20] or '',
            'lastname': partner_last_name and partner_last_name[:20] or '',
            'email': (
                self.partner_email
                if self.partner_email and len(self.partner_email) <= 50
                else ''
            ),
            'phone': self.partner_phone and self.partner_phone[:20] or '',
            'type': 'purchase',
            'payment_option': payment_option,
            'amount': rounded_amount,
            'payment_gate': 0,
            'merchant_id': merchant_id,
            'currency': self.currency_id.name,
            'skip_success_page': 1,
            'return_url': webhook_url,
            'continue_success_url': urljoin(base_odoo_url, '/payment/status'),
        }

        rendering_values.update(
            {
                'hash': self.provider_id._payway_calculate_payment_secure_hash(
                    api_key, rendering_values
                )
            }
        )

        return rendering_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Override of `payment` to find the transaction based on the notification data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: payment.transaction
        :raise ValidationError: If inconsistent data were received.
        :raise ValidationError: If the data match no transaction.
        """

        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'aba_payway' or len(tx) == 1:
            return tx

        tran_id = notification_data.get('tran_id', '')
        if not tran_id:
            raise ValidationError(
                _("No transaction identifier received from ABA Payway.")
            )

        # Currently using order reference as transaction id for payway
        # So we use tran_id to search in reference and provider_code
        tx = self.search(
            [('reference', '=', tran_id), ('provider_code', '=', 'aba_payway')]
        )
        if not tx:
            raise ValidationError(_("No transaction found for the given identifier."))

        return tx

    def _process_notification_data(self, notification_data):
        """Update the transaction state and the provider reference based on the notification data.

        This method should usually not be called directly. The correct method to call upon receiving
        notification data is :meth:`_handle_notification_data`.

        For a provider to handle transaction processing, it must overwrite this method and process
        the notification data.

        Note: `self.ensure_one()`

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        """
        self.ensure_one()

        super()._process_notification_data(notification_data)
        if self.provider_code != 'aba_payway':
            return

        if self.state == 'done':
            _logger.info(
                "The transaction with reference %s has already been processed as done; "
                "skipping notification data processing.",
                self.reference,
            )
            return

        tran_id = notification_data.get('tran_id', '')
        response = self.provider_id._payway_api_check_transaction(tran_id)

        status_code = response['status']['code']
        status_msg = response['status']['message']
        if status_code != '00':
            _logger.warning(
                "PayWay transaction return with the following errors: %s: %s; "
                "reference %s; transaction id %s.",
                status_code,
                status_msg,
                self.reference,
                tran_id,
            )
            self._set_error(
                "PayWay: " + _("Error code: %s, message: %s", status_code, status_msg)
            )
            return

        payment_code = int(response['data']['payment_status_code'])
        # Update the provider reference.
        self.provider_reference = response['data']['apv']

        if self.payment_method_id.code == 'card':
            payway_transaction_detail: dict = (
                self.provider_id._payway_api_get_transaction_detail(tran_id)
            )
            payment_method_type = (
                payway_transaction_detail.get('data', {})
                .get('payment_type', '')
                .lower()
            )

            payment_method = self.env['payment.method']._get_from_code(
                payment_method_type, mapping=const.PAYWAY_PAYMENT_METHODS_MAPPING
            )
            self.payment_method_id = payment_method or self.payment_method_id

        if payment_code == 0:
            self._set_done()
        elif payment_code in list(const.STATUS_CODE_MAPPING.keys()):
            payment_msg = (
                response['data']['payment_status']
                or const.STATUS_CODE_MAPPING[payment_code]
            )

            if payment_code == 2:
                self._set_pending(
                    _(
                        "Your payment is being processed with (payment code %(payment_code)s; message = %(payment_msg)s; "
                        "payway reference %(provider_reference)s; transaction id %(tran_id)s)",
                        payment_code=payment_code,
                        payment_msg=payment_msg,
                        provider_reference=self.provider_reference,
                        tran_id=tran_id,
                    )
                )
            else:
                self._set_error(
                    _(
                        "An error occurred during the processing of your payment (payment code %(payment_code)s; message = %(payment_msg)s; "
                        "payway reference %(provider_reference)s; transaction id %(tran_id)s). Please try again.",
                        payment_code=payment_code,
                        payment_msg=payment_msg,
                        provider_reference=self.provider_reference,
                        tran_id=tran_id,
                    )
                )
        else:
            _logger.warning(
                "Received data with invalid payment code: (%s) for transaction with "
                "payway reference %s; transaction id %s",
                payment_code,
                self.reference,
                tran_id,
            )
            self._set_error(
                "ABA Payway: "
                + _(
                    "Unknown payment code: %(payment_code)s; payway reference %(provider_reference)s; transaction id %(tran_id)s",
                    payment_code=payment_code,
                    provider_reference=self.provider_reference,
                    tran_id=tran_id,
                )
            )
