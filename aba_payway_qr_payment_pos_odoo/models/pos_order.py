from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.aba_payway_qr_payment_pos_odoo import const


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _payway_get_refund_source_transaction_id(self):
        self.ensure_one()

        refunded_lines = self.lines.filtered("refunded_orderline_id")
        if not refunded_lines:
            raise UserError(_("PayWay refund is only available for refund orders."))

        source_orders = refunded_lines.mapped("refunded_orderline_id.order_id")
        if len(source_orders) != 1:
            raise UserError(
                _(
                    "This refund contains lines from multiple orders "
                    "and cannot be processed with PayWay."
                )
            )

        source_payway_payments = source_orders.payment_ids.filtered(
            lambda payment: payment.amount > 0
            and payment.transaction_id
            and payment.payment_method_id.payment_method_type == "qr_code"
            and payment.payment_method_id.qr_code_method in const.PAYMENT_METHODS_CODES
        )
        if len(source_payway_payments) != 1:
            raise UserError(
                _(
                    "Unable to determine the original PayWay transaction. "
                    "Please refund from an order with one PayWay payment."
                )
            )

        return source_payway_payments[0].transaction_id

    def _payway_process_backend_refund_payment(self, payment):
        self.ensure_one()
        if not payment or payment.amount >= 0 or payment.transaction_id:
            return

        payment_method = payment.payment_method_id
        is_payway_qr = (
            payment_method.payment_method_type == "qr_code"
            and payment_method.qr_code_method in const.PAYMENT_METHODS_CODES
        )
        if not is_payway_qr:
            return

        source_transaction_id = self._payway_get_refund_source_transaction_id()
        refund_amount = abs(payment.amount)

        is_refund_complete = payment_method.payway_refund_transaction(
            source_transaction_id, refund_amount
        )
        if not is_refund_complete:
            raise UserError(_("PayWay refund failed. Please try again."))

        payment.transaction_id = source_transaction_id

    def add_payment(self, data):
        self.ensure_one()

        previous_payment_ids = set(self.payment_ids.ids)
        result = super().add_payment(data)
        created_payment = self.payment_ids.filtered(
            lambda payment: payment.id not in previous_payment_ids
        )[:1]
        self._payway_process_backend_refund_payment(created_payment)
        return result

