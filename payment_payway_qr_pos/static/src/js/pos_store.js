import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";


patch(PosStore.prototype, {

    // async setup() {
    //     await super.setup(...arguments);

    //     // This connects the WebSocket for QR payment updates
    //     this.data.connectWebSocket("QR_PAYMENT_STATUS_UPDATE", () => {
    //         const currentOrder = this.get_order();
    //         if (!currentOrder) {
    //             return;
    //         }
    //         const pendingQRLine = currentOrder.paymentlines.find(
    //             (line) =>
    //                 line.payment_method_id.payment_method_type === "qr_code" &&
    //                 line.get_payment_status() === "pending" // Or 'waitingCard' depending on your line status
    //         );

    //         if (pendingQRLine) {
    //             // Call a method on your payment interface to handle the status update
    //             pendingQRLine.payment_method_id.payment_terminal.handleQRPaymentStatusResponse();
    //         }
    //     });
    // },

    async showQR(payment) {
        // Add your custom logic here
        // For example, add context or call backend
        // Example: this.env.services.user.updateContext(...)
              
        user.updateContext({ 
            model: "pos.order", 
            model_id: payment.pos_order_id.uuid,
            qr_tran_id: payment.pos_order_id.pos_reference
        });

        console.log(payment);

        return await super.showQR(payment);
    },
});