import { QRPopup } from "@point_of_sale/app/utils/qr_code_popup/qr_code_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { onMounted, onWillUnmount, onWillStart } from "@odoo/owl";

const FIFTENNSEC = 15 * 1000;
const PAYWAYQRCODEMETHOD = ['alipay', 'wechat', 'abapay_khqr'];

patch(QRPopup.prototype, {

    setup() {
        super.setup(...arguments);

        this.orm = useService("orm");

        this.state = useState({
            qr_code_method: "",
            qrLifetime: 0,
            dynamic_body: this.props.body,
            pollingInProgress: false,
            countDown: null,
        });

        // Odoo bus service for webhook notifications
        this.busService = this.env.services.bus_service;
        this.channelName = "pos.order.payment.payway." + this.props.order.pos_reference.split(" ").at(-1);
        this._notificationHandler = this._onBusNotification.bind(this);
        this.busService.addChannel(this.channelName);
        this.busService.subscribe("notification", this._notificationHandler);

        this.intervalPollingTimer = null;
        this.pollingStartTime = null;
        this.countDownTimer = null;

        console.log(this);

        onWillStart(async () => {
            await this._initializePaywayQRPayment();
        });

        onWillUnmount(() => {
            this.busService.deleteChannel(this.channelName);
            this.busService.unsubscribe("notification", this._notificationHandler);
            this._clearAllPaymentTimers();
        });
    },

    async _confirm() {
        // When button click confirm

        if (PAYWAYQRCODEMETHOD.includes(this.state.qr_code_method)) {
            this.setButtonsDisabled(true);
            let is_payment_complete = false;
            try {
                is_payment_complete = await this.orm.call("pos.payment.method", "payway_verify_transaction", [
                    [this.props.line.payment_method_id.id],
                    this.props.order.pos_reference,
                ]);

            }
            catch (error) {
                console.log(error)
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Failure"),
                    body: _t("Failure to verify Payway QR payment status"),
                });
                this.setButtonsDisabled(false);
                return false;
            }


            if (!is_payment_complete) {
                // Payment return uncomplete
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Payment Status Update"),
                    body: _t("Payment Status returns unpaid"),
                });
                this.setButtonsDisabled(false);
                return false;
            }

            this.setButtonsDisabled(false);
        }

        return super._confirm();
    },

    async _cancel() {

        if (PAYWAYQRCODEMETHOD.includes(this.state.qr_code_method)) {
            await this.orm.call("pos.payment.method", "payway_cancel_transaction", [
                [this.props.line.payment_method_id.id],
                this.props.order.pos_reference,
            ])
        };

        this._clearAllPaymentTimers();
        super._cancel();
    },

    async _onBusNotification(notification) {
        console.log(notification);
        this._confirm();
    },

    async _initializePaywayQRPayment() {

        const pm_line = this.props.line;
        let qr_code_method = '';

        try {
            // Fetch QR Payment Method from the server
            qr_code_method = await this.orm.call("pos.payment.method", "get_payway_qr_code_method", [
                [pm_line.payment_method_id.id]
            ]);
            this.state.qr_code_method = qr_code_method;

            if (PAYWAYQRCODEMETHOD.includes(qr_code_method)) {
                this.state.dynamic_body = "Awaiting Payments...";

                // Fetch the qr life time (in minute)
                let qrLifetime = await this.orm.call("pos.payment.method", "get_payway_qr_lifetime", [
                    [pm_line.payment_method_id.id]
                ]);
                this.state.qrLifetime = qrLifetime;
                console.log(this.state.qrLifetime);

                this._startPaymentCountDown(this.state.qrLifetime * 60);
                this.pollingStartTime = Date.now();
                this._startPaymentPollingVerification();
            }

        } catch (error) {
            console.error("Error fetching QR payment method:", error);
            return;
        }
    },


    async _verifyQrPaymentStatus() {
        if (!this.state.pollingInProgress) {
            return;
        }

        if (!PAYWAYQRCODEMETHOD.includes(this.state.qr_code_method)) {
            this._clearAllPaymentTimers();
            this.state.pollingInProgress = false;
            return;
        }

        console.log("Attempting to verify Payway QR...");
        let is_payment_complete = false;
        try {
            is_payment_complete = await this.orm.call("pos.payment.method", "payway_verify_transaction", [
                [this.props.line.payment_method_id.id],
                this.props.order.pos_reference,
            ]);

        } catch (error) {
            console.error("Error during Payway verification:", error);
            return;
        }

        if (is_payment_complete) {
            console.log("Payment complete! Proceeding with confirmation.");
            this._clearAllPaymentTimers();
            this.state.pollingInProgress = false;
            return super._confirm();

        } else {
            console.log("Payment not success yet.");
        }
    },

    _startPaymentPollingVerification() {
        if (!PAYWAYQRCODEMETHOD.includes(this.state.qr_code_method)) {
            return;
        }

        this.state.pollingInProgress = true;

        // Call every 15 seconds
        this.intervalPollingTimer = setInterval(() => {
            const elapsedTime = Date.now() - this.pollingStartTime;
            const qrLifetime = this.state.qrLifetime * 60 * 1000;

            if (elapsedTime < qrLifetime) {
                this._dispatchIdlePreventionEvent();
                this._verifyQrPaymentStatus();
            }
            else {
                // Stop polling after qr expirse
                this._clearAllPaymentTimers();
                this.state.pollingInProgress = false;
                console.log("QR Payment polling stopped.");

                // Close popup
                super._cancel();
            }

        }, FIFTENNSEC);
    },


    _startPaymentCountDown(duration) {
        if (!PAYWAYQRCODEMETHOD.includes(this.state.qr_code_method)) {
            return;
        }

        let timer = duration, minutes, seconds;

        if (this.countDownTimer) {
            clearInterval(this.countDownTimer);
        };

        this.countDownTimer = setInterval(() => {
            minutes = parseInt(timer / 60, 10);
            seconds = parseInt(timer % 60, 10);

            minutes = minutes < 10 ? "0" + minutes : minutes;
            seconds = seconds < 10 ? "0" + seconds : seconds;

            this.state.countDown = minutes + ":" + seconds;

            if (--timer < 0) {
                clearInterval(this.countDownTimer);
            }
        }, 1000);
    },

    _clearAllPaymentTimers() {
        if (this.intervalPollingTimer) {
            clearInterval(this.intervalPollingTimer);
            this.intervalPollingTimer = null;
        }
        if (this.countDownTimer) {
            clearInterval(this.countDownTimer);
            this.countDownTimer = null;
        }
    },

    // Dispatch a mousemove event to prevent POS idle timeout
    _dispatchIdlePreventionEvent() {
        const event = new MouseEvent('mousemove', {
            view: window,
            bubbles: true,
            cancelable: true,
            clientX: 0,
            clientY: 0,
        });
        window.dispatchEvent(event);
        console.log("Dispatched mousemove event to prevent POS idle timeout.");
    },
});