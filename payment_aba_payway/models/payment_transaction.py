from datetime import datetime
import pprint
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

    def _compute_reference(self, provider_code, prefix=None, separator='-', **kwargs):
        """Override of `payment` to ensure that PayWay requirement for references is satisfied.

        PayWay requires for references to be at most 20 characters long.
        Make sure that on DB change, the PayWay transaction id will not be duplicate.
        Preserve Odoo original reference in PayWay transaction id for easy reconciliation.

        """

        if provider_code != 'aba_payway':
            return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

        if not prefix:
            # TODO: Why do we need to encode timestamp to base62? Timestamps will already be unique?
            # ANSWER: PayWay requires transaction reference to be at most 20 characters long, so base62 shorten the length. 

            # Use custom prefix, by convert timestamp to base62
            # preserve Odoo original reference in PayWay transaction id for easy reconciliation.
            # Also ensure consitency with PayWay transaction id for POS module (Same prefix format).

            reference_suffix = self.provider_id._compute_transaction_suffix()
            reference = self.sudo()._compute_reference_prefix(
                provider_code, separator, **kwargs
            )
            # reference = super()._compute_reference(provider_code, prefix=prefix, **kwargs)

            prefix = f'{reference}{separator}{reference_suffix}'

        return super()._compute_reference(provider_code, prefix=prefix, **kwargs)

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

        api_url, merchant_id, api_key, _ = self.provider_id._payway_get_api_cred()

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
            'type': 'pre-auth' if self.provider_id.capture_manually else 'purchase',
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
    
    def _send_refund_request(self, amount_to_refund=None):
        """ Override of payment to send a refund request to Stripe.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund.
        :return: The refund transaction created to process the refund request.
        :rtype: recordset of `payment.transaction`
        """
        refund_tx = super()._send_refund_request(amount_to_refund=amount_to_refund)
        if self.provider_code != 'aba_payway':
            return refund_tx
        
        _, merchant_id, _, public_key_pem = self.provider_id._payway_get_api_cred()

        payload_merchant_auth = {
            "mc_id": merchant_id,
            "tran_id": self.reference,
            "refund_amount": -refund_tx.amount,
        }
        merchant_auth = self.provider_id._payway_calculate_merchant_auth(public_key_pem, payload_merchant_auth)

        data: dict = self.provider_id._payway_api_refund_transaction(merchant_auth)
        _logger.info(
            "Payway refund request response for transaction wih reference %s:\n%s",
            self.reference, pprint.pformat(data)
        )

        # Prepare data for _process_notification_data to handle
        data.update({
            'payment_status': const.STATUS_MAPPING['REFUNDED'],
            'apv': self.provider_reference,
        })

        refund_tx._handle_notification_data('aba_payway', data)

        return refund_tx

    def _send_capture_request(self, amount_to_capture=None):
        """ Override of `payment` to send a capture request to Adyen. """
        capture_child_tx = super()._send_capture_request(amount_to_capture=amount_to_capture)
        if self.provider_code != 'aba_payway':
            return capture_child_tx 

        _, merchant_id, _, public_key_pem = self.provider_id._payway_get_api_cred()        
        payload_merchant_auth = {
            "mc_id": merchant_id,
            "tran_id": self.reference,
            "complete_amount": amount_to_capture or self.amount,
        }
        merchant_auth = self.provider_id._payway_calculate_merchant_auth(public_key_pem, payload_merchant_auth)
        
        data: dict = self.provider_id._payway_api_capture_transaction(merchant_auth)
        _logger.info(
            "Payway capture request response for transaction wih reference %s:\n%s",
            self.reference, pprint.pformat(data)
        )

        # Prepare data for _process_notification_data to handle
        data.update({
            'payment_status': const.STATUS_MAPPING['APPROVED'],
            'apv': self.provider_reference,
        })
        self._handle_notification_data('aba_payway', data)

        if capture_child_tx:
            capture_child_tx._handle_notification_data('aba_payway', data)

        return capture_child_tx 

    def _send_void_request(self, amount_to_void=None):
        """ Override of `payment` to send a void request to Adyen. """
        child_void_tx = super()._send_void_request(amount_to_void=amount_to_void)

        if self.provider_code != 'aba_payway':
            return child_void_tx
        
        # NOTE:
        # Payway automatically void the remaining balance upon partial capture.
        # Calling the cancelled API in this case will result in an error. we skip the cancel API request 
        # if a capture has already occurred and directly void the remaining balance.
        # 
        # Logic:
        # - 'authorized': No capture has occurred yet; proceed with cancellation.
        # - 'done': Partial captured; skip API, update Odoo locally.
        if self.state != "done":

            _, merchant_id, _, public_key_pem = self.provider_id._payway_get_api_cred()
            payload_merchant_auth = {
                "mc_id": merchant_id,
                "tran_id": self.reference,
            }

            merchant_auth = self.provider_id._payway_calculate_merchant_auth(public_key_pem, payload_merchant_auth)
            data: dict = self.provider_id._payway_api_void_transaction(merchant_auth)
            _logger.info(
                "Payway cancel request response for transaction wih reference %s:\n%s",
                self.reference, pprint.pformat(data)
            )

            # Prepare data for _process_notification_data to handle
            data.update({
                'payment_status': const.STATUS_MAPPING['CANCELLED'],
                'apv': self.provider_reference,
            })
        
        else:
            data = {
                'payment_status': const.STATUS_MAPPING['CANCELLED'],
                'apv': self.provider_reference,
            }

            _logger.info(
                "Payway transaction wih reference %s already in 'Done' state, skipping void API call.",
                self.reference
            )

        self._handle_notification_data('aba_payway', data)

        if child_void_tx:
            child_void_tx._handle_notification_data('aba_payway', data)
        
        return child_void_tx


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

        # NOTE: Without check transaction API, We need to set payment status manually
        # to distinguish between status of transaction.

        self.ensure_one()

        super()._process_notification_data(notification_data)
        if self.provider_code != 'aba_payway':
            return
        
        payment_status = notification_data.get('payment_status')
        
        # Update the provider reference.
        self.provider_reference = notification_data.get('apv')
        
        if (
            (
                payment_status == const.STATUS_MAPPING["APPROVED"]
                or payment_status == const.STATUS_MAPPING["PRE-AUTH"]
            )
            and self.state not in ('done', 'authorized')
        ):
            # If tran_id exist, this mean the data come from webhook after complete the payment
            tran_id = notification_data.get('tran_id', '')

            if self.payment_method_id.code == 'card' and tran_id:
                try:
                    payway_transaction_detail: dict = self.provider_id._payway_api_get_transaction_detail(tran_id)
                    payment_method_type = payway_transaction_detail.get('data', {}).get('payment_type', '').lower()

                    payment_method = self.env['payment.method']._get_from_code(
                        payment_method_type, mapping=const.PAYWAY_PAYMENT_METHODS_MAPPING
                    )
                    self.payment_method_id = payment_method or self.payment_method_id
                    
                except ValidationError as e:
                    _logger.warning(
                        "Failed to fetch payment method details for transaction id %s; "
                        "payway reference %(provider_reference)s; Error: %s", 
                        tran_id, self.provider_reference, str(e)
                    )

        if  (
            payment_status == const.STATUS_MAPPING["APPROVED"]
            or payment_status == const.STATUS_MAPPING["REFUNDED"]
        ):
            
            self._set_done()
            
            # Immediately post-process the transaction if it is a refund, as the post-processing
            # will not be triggered by a customer browsing the transaction from the portal.
            if self.operation == 'refund':
                self.env.ref('payment.cron_post_process_payment_tx')._trigger()
        
        elif payment_status == const.STATUS_MAPPING["PRE-AUTH"]:
            self._set_authorized()

        elif payment_status == const.STATUS_MAPPING["CANCELLED"]:
            self._set_canceled()

        else:
            _logger.warning(
                "Received data with invalid payment status: (%s) for transaction with "
                "payway reference %s; transaction id %s", payment_status, self.provider_reference, tran_id
            )

            self._set_pending(_(
                "Received unknown payment status: %(payment_status)s; payway reference %(provider_reference)s; transaction id %(tran_id)s", 
                payment_status=payment_status, provider_reference=self.provider_reference, tran_id=tran_id
            ))