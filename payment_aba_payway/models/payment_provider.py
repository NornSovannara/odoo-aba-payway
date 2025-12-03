from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo import _, models, fields, api

from odoo.addons.payment_aba_payway import const

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('aba_payway', "ABA PayWay")], ondelete={'aba_payway': 'set default'}
    )

    @api.depends('code')
    def _compute_view_configuration_fields(self):        
        super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.code == 'aba_payway').update({
            'require_currency': True,
        })

    # ==== CONSTRAINT METHODS ===#
    def _get_supported_currencies(self):
        """ Override of `payment` to return the supported currencies. """
        supported_currencies = super()._get_supported_currencies()
        if self.code == 'aba_payway':
            supported_currencies = supported_currencies.filtered(
                lambda c: c.name in const.SUPPORTED_CURRENCIES
            )
        return supported_currencies

    def _payway_get_api_cred(self):
        """Return the URL of the API corresponding to the selected payway environment.
        API cred is configured on the bank account module.

        :return: (API URL, Merchant ID, API Key).
        :rtype: (str, str, str)
        """
        self.ensure_one()
        return self.journal_id.bank_account_id._payway_get_api_cred()
    
    def _payway_calculate_payment_secure_hash(
            self, 
            api_key: str, 
            payload: dict, 
            secure_hash_keys: list = const.PURCHASE_PAYMENT_SECURE_HASH_KEYS
        ):
        
        self.ensure_one()
        return self.journal_id.bank_account_id._payway_calculate_payment_secure_hash(api_key, payload, secure_hash_keys)

    def _payway_api_check_transaction(self, tran_id: str):
        self.ensure_one()
        return self.journal_id.bank_account_id._payway_api_check_transaction(tran_id)

    def _payway_api_get_transaction_detail(self, tran_id: str):
        self.ensure_one()
        return self.journal_id.bank_account_id._payway_api_get_transaction_detail(tran_id)

    def _payway_calculate_webhook_secure_hash(self, notification_data):
        self.ensure_one()

        _, _, api_key = self._payway_get_api_cred()
        return self.journal_id.bank_account_id._payway_calculate_webhook_secure_hash(api_key, notification_data)

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'aba_payway':
            return default_codes
        return const.DEFAULT_PAYMENT_METHODS_CODES
