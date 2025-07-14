import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

const PAYWAYQRCODEMETHOD = ['alipay', 'wechat', 'abapay_khqr'];

patch(PosStore.prototype, {

    async setup() {
        await super.setup(...arguments);
        console.log("POS Store", this);
        console.log("POS Store idleTimeout: ", super.idleTimeout);
    },

    async showQR(payment) {

        // When user click on QR button in payment screen
        user.updateContext({
            model: "pos.order",
            qr_type: "screen",
            qr_tran_id: payment.pos_order_id.pos_reference
        });

        console.log(payment.pos_order_id.pos_reference);
        console.log("Payment: ", payment);

        return await super.showQR(payment);
    },
});