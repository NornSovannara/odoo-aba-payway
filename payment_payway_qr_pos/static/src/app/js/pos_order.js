import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { useState } from "@odoo/owl";

patch(PosOrder.prototype, {

    getCustomerDisplayData() {
        const data = super.getCustomerDisplayData();
        const selectedPaymentLine = this.get_selected_paymentline();

        if (selectedPaymentLine && selectedPaymentLine.qrPaymentData) {

            // add qrCodeMethod to qrPaymentData to use in qr customer display
            data.qrPaymentData.qrCodeMethod = selectedPaymentLine.payment_method_id.qr_code_method || '';
        }

        return data
    },
});