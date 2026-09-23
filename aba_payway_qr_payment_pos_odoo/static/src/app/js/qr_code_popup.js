import { registry } from "@web/core/registry";
import { QRPopup } from "@point_of_sale/app/utils/qr_code_popup/qr_code_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { PAYWAY_QR_CODE_METHOD } from "./const";

const POLL_INTERVAL_MS = 3 * 1000;
const SUCCESS_VIEW_DURATION_MS = 5 * 1000;
const formatCurrency = registry.subRegistries.formatters.content.monetary[1];

QRPopup.props = {
    ...(QRPopup.props || {}),
    title: {
        validate: (m) =>
            m === false ||
            typeof m === "string" ||
            (typeof m === "object" && typeof m?.toString === "function"),
        optional: true,
    },
};

patch(QRPopup.prototype, {

    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");

        if (!this.props.title) {
            this.props.title = this.props.line.payment_method_id.name || "";
            this.props.body = _t("Please scan the QR code with %s", this.props.title);
        }

        const qrCodeMethod = this.props.line.payment_method_id.qr_code_method
        const digitalQrLifetime = this.props.line.payment_method_id.digital_qr_lifetime
        this.paywayQRState = useState({
            qrCodeMethod: qrCodeMethod,
            DigitalQrLifetime: digitalQrLifetime,
            pollingInProgress: false,
            countDown: null,

            currency_name: this.props.order.currency.name,
            displayAmount: formatCurrency(this.props.line.amount || 0, false),
            merchantDisplayName: this.props.order.session.config_id.display_name,

            paymentComplete: false,
        });

        this.intervalPollingTimer = null;
        this.pollingStartTime = null;
        this.countDownTimer = null;
        this.successViewTimer = null;

        onMounted(() => {
            if (PAYWAY_QR_CODE_METHOD.includes(qrCodeMethod)) {
                this._initializePaywayQRPayment();
                this._loadPaywayCheckoutUrl();
            }
        });

        onWillUnmount(() => {
            this._clearAllPaymentTimers();
        });
    },

    async _loadPaywayCheckoutUrl() {
        try {
            const url = await this.orm.call("pos.payment.method", "payway_get_checkout_url", [
                [this.props.line.payment_method_id.id],
                this.props.line.transaction_id,
            ]);
            if (url) {
                // Store on the payment line only: the CUSTOMER display embeds the
                // iframe from this. The cashier keeps its own KHQR card layout.
                const line = this.props.line;
                if (line.qrPaymentData) {
                    line.qrPaymentData = { ...line.qrPaymentData, checkoutUrl: url };
                }
            }
        } catch {
            // Silent fallback: the in-template QR card keeps rendering.
        }
    },

    async _confirm() {
        // When button click confirm

        if (PAYWAY_QR_CODE_METHOD.includes(this.paywayQRState.qrCodeMethod)) {
            this.setButtonsDisabled(true);
            let is_payment_complete = false;

            try {
                is_payment_complete = await this.orm.call("pos.payment.method", "payway_verify_transaction", [
                    [this.props.line.payment_method_id.id],
                    this.props.line.transaction_id,
                ]);

            }
            catch (error) {
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Failure"),
                    body: _t("Failed to verify Payway QR payment status."),
                });
                this.setButtonsDisabled(false);
                return false;
            }

            if (!is_payment_complete) {
                // Payment return uncomplete
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Payment Status"),
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

        try {
            if (PAYWAY_QR_CODE_METHOD.includes(this.paywayQRState.qrCodeMethod)) {
                await this.orm.call("pos.payment.method", "payway_cancel_transaction", [
                    [this.props.line.payment_method_id.id],
                    this.props.line.transaction_id,
                ])
            };
        }
        catch { }

        this._clearAllPaymentTimers();
        super._cancel();
    },

    async _initializePaywayQRPayment() {
        try {
            this._startPaymentCountDown(this.paywayQRState.DigitalQrLifetime * 60);
            this.pollingStartTime = Date.now();
            this._startPaymentPollingVerification();

        } catch (error) {
            return;
        }
    },

    async _verifyQrPaymentStatus() {
        if (!this.paywayQRState.pollingInProgress) {
            return;
        }

        let is_payment_complete = false;
        try {
            is_payment_complete = await this.orm.call("pos.payment.method", "payway_verify_transaction", [
                [this.props.line.payment_method_id.id],
                this.props.line.transaction_id,
            ]);

        } catch {
            return;
        }

        if (is_payment_complete) {
            this._clearAllPaymentTimers();
            this.paywayQRState.pollingInProgress = false;
            this._showSuccessAndConfirm();
        }
    },

    _showSuccessAndConfirm() {
        this.paywayQRState.paymentComplete = true;
        this.setButtonsDisabled(true);
        // Flag the payment line so Odoo's customer-display sync swaps the
        // customer screen to the success view.
        const line = this.props.line;
        if (line?.qrPaymentData) {
            line.qrPaymentData = { ...line.qrPaymentData, paymentComplete: true };
        }
        // Capture super._confirm outside setTimeout: `super` is not resolvable inside the arrow callback.
        const superConfirm = super._confirm.bind(this);
        this.successViewTimer = setTimeout(() => {
            this.successViewTimer = null;
            superConfirm();
        }, SUCCESS_VIEW_DURATION_MS);
    },

    _startPaymentPollingVerification() {

        this.paywayQRState.pollingInProgress = true;

        // Poll the payment status frequently so the customer-display Thank-you
        // flips close to ABA's own success animation.
        this.intervalPollingTimer = setInterval(() => {
            const elapsedTime = Date.now() - this.pollingStartTime;
            const qrLifetime = this.paywayQRState.DigitalQrLifetime * 60 * 1000;

            if (elapsedTime < qrLifetime) {
                this._dispatchIdlePreventionEvent();
                this._verifyQrPaymentStatus();
            }
            else {
                this._clearAllPaymentTimers();
                this.paywayQRState.pollingInProgress = false;
                super._cancel();
            }

        }, POLL_INTERVAL_MS);
    },

    _startPaymentCountDown(duration) {

        let timer = duration, minutes, seconds;

        if (this.countDownTimer) {
            clearInterval(this.countDownTimer);
        };

        this.countDownTimer = setInterval(() => {
            minutes = parseInt(timer / 60, 10);
            seconds = parseInt(timer % 60, 10);

            minutes = minutes < 10 ? "0" + minutes : minutes;
            seconds = seconds < 10 ? "0" + seconds : seconds;

            this.paywayQRState.countDown = minutes + ":" + seconds;

            if (--timer < 0) {
                clearInterval(this.countDownTimer);
                this.countDownTimer = null;
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
        if (this.successViewTimer) {
            clearTimeout(this.successViewTimer);
            this.successViewTimer = null;
        }
    },

    /**
     * Dispatches a mousemove event to prevent the POS idle timeout.
     * This is crucial for maintaining the QR popup untill it expire even no interaction is happening.
     */
    _dispatchIdlePreventionEvent() {
        const event = new MouseEvent('mousemove', {
            view: window,
            bubbles: true,
            cancelable: true,
            clientX: 0,
            clientY: 0,
        });
        window.dispatchEvent(event);
    },
});