import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(PosOrder.prototype, {

    getCustomerDisplayData() {

        // Try to push some qr_payment_method value to customer display data
        // To allow it to determine if the QR code belong to Payway
        let qr_code_method_id = ''
        const qr_payment = this.payment_ids.at(-1);

        if (qr_payment && qr_payment.payment_method_id.id) {
            qr_code_method_id = qr_payment.payment_method_id.id
        }
        console.log("qr_code_method_id: ", qr_code_method_id);

        return {
            qr_code_method_id: qr_code_method_id,
            ...super.getCustomerDisplayData(),
        }
    },
});