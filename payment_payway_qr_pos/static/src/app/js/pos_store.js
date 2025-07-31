import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

import { PAYWAYQRCODEMETHOD, MODEL, POS_ORDER_QR_TYPE } from "./const";

patch(PosStore.prototype, {

    async showQR(payment) {
        user.updateContext({
            model: MODEL,
            qr_type: POS_ORDER_QR_TYPE["screen"],
            qr_tran_id: payment.pos_order_id.pos_reference
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
            PAYWAYQRCODEMETHOD.includes(payment.payment_method_id.qr_code_method) &&
            payment.payment_method_id.allow_qr_on_bill
        ) {
            // Count number of printed bill for payway QR
            order.payway_bill_nb_print = (order.payway_bill_nb_print || 0) + 1;
        }
        return res;
    }
});