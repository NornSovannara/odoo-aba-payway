import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";

import { PAYWAY_QR_CODE_METHOD, MODEL, POS_ORDER_QR_TYPE, BASE62, PAYWAY_TRAN_ID_MAX_LENGTH } from "./const";

patch(PosStore.prototype, {

    async showQR(payment) {
        const order = this.get_order();

        if (PAYWAY_QR_CODE_METHOD.includes(payment.payment_method_id.qr_code_method)) {
            // Sync order to server before QR generation to enable server-side validation
            // of amount and currency, preventing tampering at the RPC call level.
            // Only done for PayWay methods — other providers are not affected.
            try {
                await this.syncAllOrders({ orders: [order] });
            } catch (error) {
                console.warn("PayWay: order sync before QR generation failed.", error);
                throw new Error(_t("PayWay: Unable to sync order before generating QR. Please check your connection and retry."));
            }

            const items = order.lines.map(line => ({
                name: line.full_product_name,
                quantity: line.qty,
                price: line.price_unit,
            }));

            user.updateContext({
                model: MODEL,
                qr_type: POS_ORDER_QR_TYPE["screen"],
                qr_tran_id: payment.transaction_id,
                order_uid: order.uuid,
                items: items,
            });
        }

        return await super.showQR(payment);
    },

    async printReceipt({
        basic = false,
        order = this.get_order(),
        printBillActionTriggered = false,
    } = {}) {
        const res = await super.printReceipt({ basic, order, printBillActionTriggered });
        const payment = order.payment_ids.at(-1);

        if (
            printBillActionTriggered &&
            payment &&
            PAYWAY_QR_CODE_METHOD.includes(payment.payment_method_id.qr_code_method) &&
            payment.payment_method_id.allow_qr_on_bill
        ) {
            // Count number of printed bill for payway QR
            order.payway_bill_nb_print = (order.payway_bill_nb_print || 0) + 1;
        }
        return res;
    },

    _toBase62(num) {
        if (num === 0) return BASE62[0];

        let result = "";
        while (num > 0) {
            const rem = num % 62;
            result = BASE62[rem] + result;
            num = Math.floor(num / 62);
        }
        return result;
    },

    _paywayCreateTxnId(payment) {

        if (payment.transaction_id) {
            // Prevent regenerating transaction_id if it already exists (e.g. when retrying payment after failure)
            return payment.transaction_id;
        }

        // Get timstamp in seconds for suffix
        const timestamp = Math.floor(Date.now() / 1000);
        const suffix = this._toBase62(timestamp);
        const lenSuffix = suffix.length;

        const orderReference = payment.pos_order_id.pos_reference.split(" ").at(-1);
        const prefix = orderReference.slice(0, PAYWAY_TRAN_ID_MAX_LENGTH - 1 - lenSuffix);

        const transaction_id = `${prefix}-${suffix}`;
        return transaction_id;
    }
});