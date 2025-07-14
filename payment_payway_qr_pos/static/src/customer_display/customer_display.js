import { patch } from "@web/core/utils/patch";
import { CustomerDisplay } from "@point_of_sale/customer_display/customer_display"

patch(CustomerDisplay.prototype, {

    setup() {
        super.setup(...arguments);
        console.log("Customer Display: ", this);
    },
})