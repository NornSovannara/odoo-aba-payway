# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo import _, models, fields, api
from odoo.addons.account_payway_qr_base import const


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def get_qr_code(
        self,
        amount,
        free_communication,
        structured_communication,
        currency,
        debtor_partner,
    ):
        self.ensure_one()
        if self.qr_code_method in const.PAYMENT_METHODS_CODES and amount == False:
            # Odoo attempt to call default qr generation with amount is False
            # which can be use when POS is offline
            # to prevent it return False when pos is offline
            return False

        return super().get_qr_code(
            amount,
            free_communication,
            structured_communication,
            currency,
            debtor_partner,
        )

    def payway_cancel_transaction(self, qr_tran_id):
        """Call res.partner.bank close payway transaction method"""

        self.ensure_one()
        if self.qr_code_method in const.PAYMENT_METHODS_CODES:
            qr_tran_id = qr_tran_id.split(" ")[-1]

            payment_bank = self.journal_id.bank_account_id
            payment_bank._payway_api_close_payway_transaction(qr_tran_id)

    def get_qr_payment_method(self):
        return self.qr_code_method

    def payway_fetch_qr_status(self, qr_tran_id):
        pass

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
