import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";


patch(PosStore.prototype, {
    async showQR(payment) {
        // Add your custom logic here
        // For example, add context or call backend
        // Example: this.env.services.user.updateContext(...)

        user.updateContext({ 
            model: "pos.order", 
            model_id: payment.pos_order_id.uuid,
            model_reference: payment.pos_order_id.pos_reference
        });

        console.log(payment.pos_order_id.payment_ids)
        console.log(payment.pos_order_id)

        return await super.showQR(payment);
    },
    
});