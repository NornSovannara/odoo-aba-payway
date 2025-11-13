/** @odoo-module */

import PaymentPostProcessing from '@payment/js/post_processing';
import { ConnectionLostError, rpc, RPCError } from '@web/core/network/rpc';

PaymentPostProcessing.include({

    pollPaywayTimeout: 10000,

    async start() {
        this._pollPayway();
        return this._super(...arguments);
    },

    _pollPayway() {
        // Waiting 10 sec for webhook to completed, if it is not complete and redirect out of this page
        // start polling payway payment status every 3 seconds

        setTimeout(async () => {
            rpc('/payment/payway/status/poll', {
                'csrf_token': odoo.csrf_token,

            }).then((postProcessingValues) => {
                let { provider_code, state } = postProcessingValues;
                if (provider_code != 'aba_payway' || this._getFinalStates(provider_code).has(state)) {
                    return;
                }
                else {
                    this.pollPaywayTimeout = 3000;
                    this._pollPayway();
                }
            }).catch(error => {
                const isRetryError = error instanceof RPCError && error.data.message === 'retry';
                const isConnectionLostError = error instanceof ConnectionLostError;
                if (isRetryError || isConnectionLostError) {
                    this.pollPaywayTimeout = 3000;
                    this._pollPayway();
                }
                if (!isRetryError) {
                    throw error;
                }
            });

        }, this.pollPaywayTimeout);
    }
})