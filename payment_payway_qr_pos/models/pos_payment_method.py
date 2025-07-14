# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo import _, models, fields, api
from odoo.addons.account_payway_qr_base import const


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    allow_qr_on_bill = fields.Boolean(
        string="Allow QR on Bill",
        help="If checked, a QR code for this payment method will be generated and printed on the customer bill.",
        default=False,
    )

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

    def get_qr_code(
        self,
        amount,
        free_communication,
        structured_communication,
        currency,
        debtor_partner,
    ):

        if (
            self.payment_method_type == 'qr_code'
            or self.qr_code_method in const.PAYMENT_METHODS_CODES
        ):

            qr_type = self._context.get('qr_type')
            if qr_type == "bill" and not self.allow_qr_on_bill:
                print("This method is not allow to print on bill")

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
        if (
            self.payment_method_type != 'qr_code'
            or not self.qr_code_method in const.PAYMENT_METHODS_CODES
        ):
            return True

        qr_tran_id = qr_tran_id.split(" ")[-1]

        payment_bank = self.journal_id.bank_account_id
        payment_bank._payway_api_close_transaction(qr_tran_id)

    def payway_verify_transaction(self, qr_tran_id):

        self.ensure_one()
        if (
            self.payment_method_type != 'qr_code'
            or not self.qr_code_method in const.PAYMENT_METHODS_CODES
        ):
            return True

        qr_tran_id = qr_tran_id.split(" ")[-1]

        payment_bank = self.journal_id.bank_account_id
        response = payment_bank._payway_api_check_transaction(qr_tran_id)

        print("Verify transaction response", response)
        is_payment_complete = str(response['data']['payment_status_code']) == '0'
        return is_payment_complete

    def get_payway_qr_code_method(self):
        print("QR Payment Method: ", self.qr_code_method, self.allow_qr_on_bill)
        return self.qr_code_method

    def get_payway_qr_lifetime(self):
        self.ensure_one()
        return self.journal_id.bank_account_id.qr_lifetime
