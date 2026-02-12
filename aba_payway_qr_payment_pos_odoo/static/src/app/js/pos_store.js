import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

import { PAYWAY_QR_CODE_METHOD, MODEL, POS_ORDER_QR_TYPE, BASE62 } from "./const";

patch(PosStore.prototype, {

    async showQR(payment) {

        user.updateContext({
            model: MODEL,
            qr_type: POS_ORDER_QR_TYPE["screen"],
            qr_tran_id: payment.transaction_id,
        });

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

        // Get timstamp in days for suffix, so that transaction id will not be too long
        const timestamp = Math.floor(Date.now() / 1000 / 60 / 60 / 24);
        const suffix = this._toBase62(timestamp);

        const orderReference = payment.pos_order_id.pos_reference.split(" ").at(-1);

        const transaction_id = `${orderReference}-${suffix}`;
        return transaction_id;
    }
});