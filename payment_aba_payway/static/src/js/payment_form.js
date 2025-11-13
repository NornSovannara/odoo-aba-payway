/** @odoo-module */

import { _t } from '@web/core/l10n/translation';
import paymentForm from '@payment/js/payment_form';
import { rpc, RPCError } from '@web/core/network/rpc';


paymentForm.include({

    /**
     * Prepare the inline form of Xendit for direct payment.
     *
     * @override method from @payment/js/payment_form
     * @private
     * @param {number} providerId - The id of the selected payment option's provider.
     * @param {string} providerCode - The code of the selected payment option's provider.
     * @param {number} paymentOptionId - The id of the selected payment option.
     * @param {string} paymentMethodCode - The code of the selected payment method, if any.
     * @param {string} flow - The online payment flow of the selected payment option.
     * @return {void}
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== 'aba_payway') {
            this._super(...arguments);
            return;
        }
        this._setPaymentFlow('direct');
    },


    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== 'aba_payway') {
            await this._super(...arguments);
            return;
        }

        // Instantiate ABA Payway checkout
        // AbaPayway is loaded from "https://checkout.payway.com.kh/plugins/checkout2-0.js"
        const abaPaywayOptions = this._prepareABAPaywayOptions(processingValues);
        AbaPayway.checkout(abaPaywayOptions);
    },

    _prepareABAPaywayOptions(processingValues) {
        return Object.assign({}, {
            'form_url': processingValues['form_url'],
            'tran_id': processingValues['tran_id'],
            'req_time': processingValues['req_time'],
            'lifetime': processingValues['lifetime'],
            'firstname': processingValues['firstname'],
            'lastname': processingValues['lastname'],
            'email': processingValues['email'],
            'phone': processingValues['phone'],
            'type': processingValues['type'],
            'payment_option': processingValues['payment_option'],
            'amount': processingValues['amount'],
            'payment_gate': processingValues['payment_gate'],
            'merchant_id': processingValues['merchant_id'],
            'currency': processingValues['currency'],
            'skip_success_page': processingValues['skip_success_page'],
            'return_url': processingValues['return_url'],
            'continue_success_url': processingValues['continue_success_url'],
            'hash': processingValues['hash'],
        });
    }
});