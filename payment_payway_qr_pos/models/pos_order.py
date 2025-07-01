from odoo import fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    # referenced in l10n_id/models/res_bank.py where we will link QRIS transactions
    # to the record that initiates the payment flow

    def confirm_qr_payment(self):
        """
        Sends a bus notification to the POS frontend to confirm a QR payment.
        This method would be called by your webhook processing logic.
        """
        print("HERE", self)
        # print(
        #     f"Sending QR payment confirmation for Order ID: {order_id}, Payment Line UUID: {payment_line_uuid}"
        # )

        # Construct a unique channel name for this specific payment line
        # channel = f'pos_qr_payment_confirm_{order_id}_{payment_line_uuid}'

        # Send the message via the Odoo Bus Service
        # 'self.env' is used here because it's a model method.
        # It's equivalent to 'request.env' if called from a controller.
        # self.env['bus.bus']._sendone(
        #     channel,
        #     'pos.qr.payment.confirmed',
        #     {
        #         'status': 'success',
        #         'payment_line_uuid': payment_line_uuid,
        #         'message': 'Payment confirmed by backend!',
        #     },
        # )
        return True
