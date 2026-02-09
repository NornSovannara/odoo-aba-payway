from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_amount


class PaymentCaptureWizard(models.TransientModel):
    _inherit = 'payment.capture.wizard'

    _is_payway_provider = fields.Boolean(compute="_compute_is_payway_provider")
    
    @api.depends("transaction_ids.provider_id")
    def _compute_is_payway_provider(self):
        for wizard in self:
            wizard._is_payway_provider = any(
                tx.provider_id.code == "aba_payway" for tx in wizard.transaction_ids
            )

    def action_capture(self):

        # TODO: Check with Odoo team, is there any concerns on enforcing void_remaining_amount here on wizard? 
        # From what I can see, there might be multiple providers in a single capture wizard session.
        # Question:
        # 1. What is the case where there are more than 1 payment provider in a single wizard? 
        # 2. Is this enforcement affect other payment provider?
        # 3. How do i enforce only for Payway provider without affecting other providers in the same wizard session?

        for wizard in self:
            if wizard._is_payway_provider and wizard.has_remaining_amount:
                # force void of remaining amount for PayWay partial captures, 
                # as PayWay does not support leaving an amount in authorized state after a partial capture
                wizard.void_remaining_amount = True
        return super().action_capture()
            



