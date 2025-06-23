import json
from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class PosQrPaymentController(http.Controller):

    @http.route('/pos/qr_payment/initiate', type='json', auth='user', methods=['POST'])
    def initiate_qr_payment(self, order_id, amount, payment_type):
        """
        Endpoint to log the initiation of a QR payment and provide text for the popup.
        """
        _logger.info(
            "Initiating QR payment for order %s, amount %s, type %s",
            order_id,
            amount,
            payment_type,
        )
        pos_order = request.env['pos.order'].browse(order_id)
        if not pos_order:
            _logger.error("POS Order not found for ID: %s", order_id)
            return {'error': 'POS Order not found.'}

        popup_text = f"Please instruct the customer to scan the {payment_type.replace('_', ' ').upper()} QR code for the amount of {amount}."

        try:
            # Create a record in our custom QR transaction model for logging initiation
            qr_transaction = request.env['pos.qr.transaction'].create(
                {
                    'order_id': pos_order.id,
                    'amount': amount,
                    'payment_type': payment_type,
                    'status': 'initiated',
                }
            )
            _logger.info("Created QR transaction log: %s", qr_transaction.name)
        except Exception as e:
            _logger.error("Failed to create QR transaction log: %s", e)
            # Do not block the POS flow if logging fails, but log the error
            pass  # Or return an error if you want to be strict

        return {'popup_message': popup_text, 'success': True}
