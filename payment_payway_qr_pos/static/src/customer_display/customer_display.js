/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CustomerDisplay } from "@point_of_sale/customer_display/customer_display";
import { CustomerFacingQR } from "@point_of_sale/customer_display/customer_facing_qr";
import { useEffect } from "@odoo/owl";

import { PaywayCustomerFacingQR } from "./payway_customer_facing_qr";

patch(CustomerDisplay.prototype, {
    setup() {
        super.setup();

        const dialogService = this.dialog;
        let currentDialogCloseFn = null;

        useEffect(
            (qrPaymentData) => {
                if (qrPaymentData) {
                    let ComponentToOpen = CustomerFacingQR;


                    if (['abapay_khqr', 'wechat', 'alipay'].includes(qrPaymentData.qrCodeMethod)) {
                        ComponentToOpen = PaywayCustomerFacingQR;
                    }

                    if (currentDialogCloseFn) {
                        currentDialogCloseFn();
                        currentDialogCloseFn = null;
                    }

                    currentDialogCloseFn = dialogService.add(ComponentToOpen, qrPaymentData, {
                        onClose: () => {
                            currentDialogCloseFn = null;
                        },
                    });

                } else {
                    currentDialogCloseFn?.();
                    currentDialogCloseFn = null;
                }
            },
            () => [this.order.qrPaymentData]
        );
    },
});