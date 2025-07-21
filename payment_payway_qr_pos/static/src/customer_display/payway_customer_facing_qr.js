import { _t } from "@web/core/l10n/translation";
import { CustomerFacingQR } from "@point_of_sale/customer_display/customer_facing_qr";

export class PaywayCustomerFacingQR extends CustomerFacingQR {
    static template = "payment_payway_qr_pos.PaywayCustomerFacingQR";
    setup() {
        super.setup();
    }
}
