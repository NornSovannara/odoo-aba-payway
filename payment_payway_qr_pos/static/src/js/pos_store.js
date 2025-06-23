import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";

patch(PosStore.prototype, {
    async showQR(payment) {
        // Add your custom logic here
        // For example, add context or call backend
        // Example: this.env.services.user.updateContext(...)
        
        user.updateContext({ model: "pos.order", model_id: payment.pos_order_id.uuid });
        return await super.showQR(payment);
    },
});