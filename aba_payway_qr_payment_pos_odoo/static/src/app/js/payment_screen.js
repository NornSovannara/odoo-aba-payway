import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { PAYWAY_QR_CODE_METHOD } from "./const";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);

        this.orm = useService("orm");
        const busService = this.env.services.bus_service;

        this.channelName = null;
        this._paywayWebhookHandler = this._onPaywayWebhookNotification.bind(this);

        onMounted(async () => {
            const order = this.pos.get_order();

            const payment = order?.payment_ids.at(-1);
            const qrCodeMethod = payment?.payment_method_id?.qr_code_method;

            if (PAYWAY_QR_CODE_METHOD.includes(qrCodeMethod) && payment?.amount > 0) {
                this.channelName = "pos.order.payment.payway." + payment.transaction_id;
                busService.addChannel(this.channelName);
                busService.subscribe("notification", this._paywayWebhookHandler);
                this._completeOrderPayway(false);
            }
        });

        onWillUnmount(() => {
            if (this.channelName) {
                busService.deleteChannel(this.channelName);
                busService.unsubscribe("notification", this._paywayWebhookHandler);
            }
        });
    },

    async deletePaymentLine(uuid) {
        const line = this.paymentLines.find((line) => line.uuid === uuid);

        const isPaywayQr =
            line?.payment_method_id?.payment_method_type === "qr_code" &&
            PAYWAY_QR_CODE_METHOD.includes(line?.payment_method_id?.qr_code_method);

        if (isPaywayQr && line.transaction_id && line.payment_method_id && line.payment_method_id.id) {
            // Cancel the QR transaction before removing the payment line
            try {
                await this.orm.call("pos.payment.method", "payway_cancel_transaction", [
                    [line.payment_method_id.id],
                    line.transaction_id,
                ]);
            } catch (error) {
                console.warn("Failed to cancel Payway transaction:", error);
                // Continue with deletion even if cancellation fails
                // The transaction might have already expired or been cancelled
            }
        }

        return super.deletePaymentLine(uuid);
    },

    async sendPaymentRequest(line) {
        const isPaywayQr =
            line.payment_method_id.payment_method_type === "qr_code" &&
            PAYWAY_QR_CODE_METHOD.includes(line.payment_method_id.qr_code_method);

        if (isPaywayQr && line.amount < 0) {
            this.pos.paymentTerminalInProgress = true;
            this.numberBuffer.capture();
            this.paymentLines.forEach((paymentLine) => {
                paymentLine.can_be_reversed = false;
            });

            const isPaymentSuccessful = await this._sendPaywayRefundRequest(line);
            this.pos.paymentTerminalInProgress = false;

            const config = this.pos.config;
            const currentOrder = line.pos_order_id;
            if (
                isPaymentSuccessful &&
                currentOrder.is_paid() &&
                config.auto_validate_terminal_payment
            ) {
                this.validateOrder(false);
            }
            return;
        }

        // Setup bus notification handler before show QR Popup
        if (isPaywayQr) {
            // Use Odoo receipt number for payway unique transaction id
            line.transaction_id = this.pos._paywayCreateTxnId(line);

            if (!this.channelName) {
                const busService = this.env.services.bus_service;

                this.channelName = "pos.order.payment.payway." + line.transaction_id;
                busService.addChannel(this.channelName);
                busService.subscribe("notification", this._paywayWebhookHandler);
            }
        }
        return super.sendPaymentRequest(line);
    },

    async _sendPaywayRefundRequest(line) {
        try {
            const sourceTransactionId = this._getPaywaySourceTransactionId(line);
            const refundAmount = Math.abs(line.amount || 0);

            const isRefundComplete = await this.orm.call(
                "pos.payment.method",
                "payway_refund_transaction",
                [[line.payment_method_id.id], sourceTransactionId, refundAmount]
            );

            if (isRefundComplete) {
                line.transaction_id = sourceTransactionId;
            }
            return line.handle_payment_response(isRefundComplete);
        } catch (error) {
            const errorMessage = error?.data?.message ?? error?.message ?? "Failed to process PayWay refund";
            this.dialog.add(AlertDialog, {
                title: _t("Refund Failed"),
                body: _t(errorMessage),
            });
            return line.handle_payment_response(false);
        }
    },

    _getPaywaySourceTransactionId(line) {
        const order = line.pos_order_id;
        const refundedLines = order.lines.filter((orderLine) => orderLine.refunded_orderline_id);
        if (!refundedLines.length) {
            throw new Error(_t("PayWay refund is only available for refund orders."));
        }

        const sourceOrderUuids = new Set(
            refundedLines
                .map((orderLine) => orderLine.refunded_orderline_id?.order_id?.uuid)
                .filter(Boolean)
        );
        if (sourceOrderUuids.size !== 1) {
            throw new Error(
                _t("This refund contains lines from multiple orders and cannot be processed with PayWay.")
            );
        }

        const [sourceOrderUuid] = [...sourceOrderUuids];
        const sourceOrder =
            this.pos.models["pos.order"].getBy("uuid", sourceOrderUuid) ||
            refundedLines[0].refunded_orderline_id.order_id;
        const paywayPayments = (sourceOrder?.payment_ids || []).filter(
            (payment) =>
                payment.amount > 0 &&
                payment.transaction_id &&
                PAYWAY_QR_CODE_METHOD.includes(payment.payment_method_id?.qr_code_method)
        );

        if (paywayPayments.length !== 1) {
            throw new Error(
                _t("Unable to determine the original PayWay transaction. Please refund from an order with one PayWay payment.")
            );
        }

        return paywayPayments[0].transaction_id;
    },

    async _completeOrderPayway(isValidateFromQRPopup) {
        /**
         * Attempt complete Order on condition:
         *  - Receive webhook callback on QR popup
         *  - Receive webhook callback on QR in printed bill
         *  - Check transaction API on QR in printed bill
         */
        const order = this.pos.get_order();
        if (!order) {
            return;
        }

        if (!isValidateFromQRPopup) {
            if (!order.payway_bill_nb_print || order.payway_bill_nb_print <= 0) {
                return;
            }
        }

        const payment = order.payment_ids.at(-1);
        if (!payment) {
            return;
        }

        if (payment.amount <= 0) {
            return;
        }

        if (!isValidateFromQRPopup) {
            if (
                !payment.payment_method_id ||
                !PAYWAY_QR_CODE_METHOD.includes(payment.payment_method_id.qr_code_method) ||
                !payment.payment_method_id.allow_qr_on_bill
            ) {
                return;
            }

        } else {
            if (
                !payment.payment_method_id ||
                !PAYWAY_QR_CODE_METHOD.includes(payment.payment_method_id.qr_code_method)
            ) {
                return;
            }
        }

        let is_payment_complete = false;
        try {
            is_payment_complete = await this.orm.call("pos.payment.method", "payway_verify_transaction", [
                [payment.payment_method_id.id],
                payment.transaction_id,
            ]);

        } catch (error) {
            return;
        }

        if (!is_payment_complete) {
            return;
        }

        this.dialog.closeAll();
        payment.handle_payment_response(true);
        this.validateOrder(false);
    },

    _onPaywayWebhookNotification(notification) {
        if (notification?.channel_name === this.channelName) {
            this._completeOrderPayway(true);
        }
    },
});
