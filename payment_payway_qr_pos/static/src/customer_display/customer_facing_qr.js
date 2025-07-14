import { patch } from "@web/core/utils/patch";
import { CustomerFacingQR } from "@point_of_sale/customer_display/customer_facing_qr"
import { useService } from "@web/core/utils/hooks";

patch(CustomerFacingQR.prototype, {

    setup() {
        super.setup(...arguments);

        this.orm = useService("orm");
        console.log("Customer Facing ORM ", this.orm);
        console.log("Customer Facing QR Component", this);

    },

    async _fetchQRPaymentMethod() {

    }
})