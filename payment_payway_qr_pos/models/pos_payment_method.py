# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo import _, models, fields, api
from odoo.addons.account_payway_qr_base import const


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    # @api.depends('payment_method_type', 'journal_id')
    # def _compute_qr(self):
    #     super()._compute_qr()

    #     for pm in self:
    #         print(pm.qr_code_method)
    #         if (
    #             pm.payment_method_type == 'qr_code'
    #             and pm.qr_code_method in const.PAYMENT_METHODS_CODES
    #         ):
    #             print(pm.qr_code_method)
    #             pm.default_qr = False

    def get_qr_code(
        self,
        amount,
        free_communication,
        structured_communication,
        currency,
        debtor_partner,
    ):
        self.ensure_one()
        if self.qr_code_method in const.PAYMENT_METHODS_CODES and amount == False:
            # Odoo attempt to call default qr generation with amount is False
            # which can be use when POS is offline
            # to prevent it return False when pos is offline
            return False

        return super().get_qr_code(
            amount,
            free_communication,
            structured_communication,
            currency,
            debtor_partner,
        )
