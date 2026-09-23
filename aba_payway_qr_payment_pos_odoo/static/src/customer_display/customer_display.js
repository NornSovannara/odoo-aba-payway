import { patch } from "@web/core/utils/patch";
import { CustomerDisplay } from "@point_of_sale/customer_display/customer_display";
import { CustomerFacingQR } from "@point_of_sale/customer_display/customer_facing_qr";
import { useEffect, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

import { PAYWAY_QR_CODE_METHOD } from "./const";

const MODULE_IMG = "/aba_payway_qr_payment_pos_odoo/static/src/img";

function _escape(text) {
    const div = document.createElement("div");
    div.textContent = text ?? "";
    return div.innerHTML;
}

function _buildKhqrPanel(qrPaymentData) {
    const method = qrPaymentData.qrCodeMethod;
    const merchant = _escape(qrPaymentData.merchantDisplayName);
    const amount = _escape(qrPaymentData.displayAmount);
    const currency = _escape(qrPaymentData.currency_name);
    const qrSrc = _escape(qrPaymentData.qrCode);

    let bannerImg, scanText, bannerClass, currencyImg, amountBlock, scanExtra;
    if (method === "abapay_khqr") {
        bannerImg = `${MODULE_IMG}/khqr.svg`;
        bannerClass = "payment-banner khqr";
        scanText = "Scan to Pay";
        scanExtra = `
            <span class="payway-scan-divider">|</span>
            <img class="payway-scan-badge" src="${MODULE_IMG}/aba-pay-chip.svg" alt="ABA PAY"/>
            <img class="payway-scan-badge" src="${MODULE_IMG}/khqr-chip.svg" alt="KHQR"/>`;
        currencyImg = `${MODULE_IMG}/bakong.svg`;
        amountBlock = `
            <div class="payment-amt-value">
                ${amount}
                <span class="payment-amt-ccy khqr">${currency}</span>
            </div>`;
    } else if (method === "alipay") {
        bannerImg = `${MODULE_IMG}/alipay.svg`;
        bannerClass = "payment-banner alipay";
        scanText = "Scan with Alipay app";
        scanExtra = "";
        currencyImg = `${MODULE_IMG}/dollar.svg`;
        amountBlock = `
            <div class="payment-amt-value">
                <span class="payment-amt-ccy">$</span>
                ${amount}
            </div>`;
    } else {
        bannerImg = `${MODULE_IMG}/wechat.svg`;
        bannerClass = "payment-banner wechat";
        scanText = "Scan with WeChat app";
        scanExtra = "";
        currencyImg = `${MODULE_IMG}/dollar.svg`;
        amountBlock = `
            <div class="payment-amt-value wechat">
                <span class="payment-amt-ccy">$</span>
                ${amount}
            </div>`;
    }

    const triangle = method === "abapay_khqr"
        ? `<div class="khqr-triangle-container"><div class="khqr-triangle"></div></div>`
        : "";

    const infoClass = method === "abapay_khqr"
        ? "payment-info khqr"
        : method === "wechat"
            ? "payment-info wechat"
            : "payment-info";

    return `
        <div class="payway-cd-inner">
            <img class="payway-cd-aba-logo" src="${MODULE_IMG}/aba-pay.svg" alt="ABA Pay Logo" />
            <div class="payment-content ${method === "abapay_khqr" ? "khqr" : ""}">
                <div>
                    <div class="${bannerClass}">
                        <img src="${bannerImg}" alt="Banner" />
                    </div>
                    ${triangle}
                    <div class="${infoClass}">
                        <div class="payment-merc-name">${merchant}</div>
                        ${amountBlock}
                    </div>
                    <div class="payment-line-divider"></div>
                </div>
                <div class="payment-qr-content ${method === "abapay_khqr" ? "khqr" : ""}">
                    <img src="${currencyImg}" alt="Currency Logo" class="payment-qr-ccy ${method === "abapay_khqr" ? "khqr" : ""}" />
                    <img src="${qrSrc}" alt="QR Code" />
                </div>
            </div>
            <p class="payment-scan-desc ${method === "abapay_khqr" ? "khqr payway-scan-inline" : ""}">
                <span>${scanText}</span>
                ${scanExtra}
            </p>
        </div>`;
}

function _buildSuccessPanel(qrPaymentData) {
    const amount = _escape(qrPaymentData.displayAmount);
    const currency = _escape(qrPaymentData.currency_name);
    return `
        <div class="payway-success-view">
            <img class="payway-success-img" src="${MODULE_IMG}/success.png" alt="Success"/>
            <div class="payway-success-label">Success</div>
            <div class="payway-success-amount">
                ${amount}
                <span class="payway-success-ccy">${currency}</span>
            </div>
        </div>`;
}

function _buildIframePanel(checkoutUrl) {
    const url = _escape(checkoutUrl);
    return `
        <iframe class="payway-cd-iframe" src="${url}" frameborder="0"
                allow="clipboard-write" title="ABA PayWay QR"></iframe>`;
}

// Fully replace the core setup: bypass Odoo's default dialog-based QR popup
// (which fires unconditionally on qrPaymentData) and drive our own left-half
// overlay for PayWay methods while preserving the default behavior for others.
patch(CustomerDisplay.prototype, {
    setup() {
        this.session = session;
        this.dialog = useService("dialog");
        this.order = useState(useService("customer_display_data"));

        let currentDialogCloseFn = null;
        let overlayEl = null;
        let currentIframeUrl = null;

        const removeOverlay = () => {
            if (overlayEl) {
                overlayEl.remove();
                overlayEl = null;
            }
            currentIframeUrl = null;
        };

        useEffect(
            (qrPaymentData) => {
                const isPaywayMethod =
                    !!qrPaymentData &&
                    PAYWAY_QR_CODE_METHOD.includes(qrPaymentData.qrCodeMethod);

                // Keep the live iframe running while the QR is still pending and the
                // same URL is embedded. Once paymentComplete arrives we fall through
                // so the iframe is torn down and the success view is shown.
                if (
                    isPaywayMethod &&
                    qrPaymentData.checkoutUrl &&
                    !qrPaymentData.paymentComplete &&
                    overlayEl &&
                    currentIframeUrl === qrPaymentData.checkoutUrl
                ) {
                    return;
                }

                if (currentDialogCloseFn) {
                    currentDialogCloseFn();
                    currentDialogCloseFn = null;
                }
                removeOverlay();

                if (!qrPaymentData) {
                    return;
                }

                if (isPaywayMethod) {
                    overlayEl = document.createElement("div");
                    overlayEl.className = "payway-cd-overlay-panel";
                    if (qrPaymentData.paymentComplete) {
                        // Payment done: show our success view (green check + amount).
                        overlayEl.innerHTML = _buildSuccessPanel(qrPaymentData);
                    } else if (qrPaymentData.checkoutUrl) {
                        // Preferred: embed the ABA-hosted QR page (CSP now allows it).
                        overlayEl.classList.add("payway-cd-overlay-panel--iframe");
                        overlayEl.innerHTML = _buildIframePanel(qrPaymentData.checkoutUrl);
                        currentIframeUrl = qrPaymentData.checkoutUrl;
                    } else {
                        // Fallback: render the QR card ourselves from qrString.
                        overlayEl.innerHTML = _buildKhqrPanel(qrPaymentData);
                    }
                    document.body.appendChild(overlayEl);
                    return;
                }

                currentDialogCloseFn = this.dialog.add(CustomerFacingQR, qrPaymentData, {
                    onClose: () => {
                        currentDialogCloseFn = null;
                    },
                });
            },
            () => [this.order.qrPaymentData]
        );
    },
});
