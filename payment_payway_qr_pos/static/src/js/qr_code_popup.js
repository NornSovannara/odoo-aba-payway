import { QRPopup } from "@point_of_sale/app/utils/qr_code_popup/qr_code_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(QRPopup.prototype, {
    
    setup() {
        super.setup(...arguments);

        this.orm = useService("orm");
        console.log(this);
        this.state = useState({
            qr_payment_method: "",
            dynamic_body: this.props.body,
        });

    
        // this.channelName = `pos.order.payment.status.${"Order 00167-009-0005"}`;
        this.busService = this.env.services.bus_service;
        this.channelName = "your_channel";

        this.boundOnBusNotification = this._onBusNotification.bind(this);

        // onMounted(() => {
        //     super.onMounted();
        //     this.busService.addChannel(this.channelName);
        //     this.busService.addEventListener("notification", this.boundOnBusNotification);
        //     console.log(`[QRPopup] Subscribed to bus channel: ${this.channelName}`);
        // });

        // onWillUnmount(() => {
        //     super.onWillUnmount();
        //     this.busService.deleteChannel(this.channelName);
        //     this.busService.removeEventListener("notification", this.boundOnBusNotification);
        //     console.log(`[QRPopup] Unsubscribed from bus channel: ${this.channelName}`);
            
        // });


        this._fetchQRPaymentMethod();
    },

    async _fetchQRPaymentMethod() {
        const pm_line = this.props.line;
        const qr_payment_method = await this.orm.call("pos.payment.method", "get_qr_payment_method", [
            [pm_line.payment_method_id.id]
        ])
        this.state.qr_payment_method = qr_payment_method
        
        if (["abapay_khqr", "wechat_pay", "alipay"].includes(qr_payment_method)) {
            this.state.dynamic_body = "Awaiting Payments...";
        }
    },

    async _confirm() {
        // When button click confirm
        
        // Allert Dialog
        // this.env.services.dialog.add(AlertDialog, {
        //     title: _t("Failure"),
        //     body: _t("Failure to verify QRIS payment status"),
        // });
        // return false
        return super._confirm();
    },

    async _cancel() {
        // When cancel button is click
        console.log("before call");
        console.log(this.props.line.payment_method_id.id)
        await this.orm.call("pos.payment.method", "payway_cancel_transaction", [
            [this.props.line.payment_method_id.id],
            this.props.order.pos_reference,
        ])

        super._cancel();
    },

    _onBusNotification(notification) {
        console.log("[QRPopup] Received raw bus notification event:", notification);

        // Odoo's bus service wraps the payload in 'detail'
        const [busChannel, messageType, payload] = notification.detail;
        super._confirm();
    },

});