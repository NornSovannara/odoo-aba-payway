# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PaymentCaptureWizard(models.TransientModel):
    _inherit = 'payment.capture.wizard'

    void_remaining_amount = fields.Boolean(
        compute='_compute_void_remaining_amount',
        store=True,
        readonly=False,
    )

    payway_auto_void = fields.Boolean(
        string="Auto-void Remainder",
        compute='_compute_payway_auto_void',
        help="PayWay automatically voids remaining amount on partial capture"
    )

    @api.depends('amount_to_capture', 'available_amount')
    def _compute_void_remaining_amount(self):
        """Auto-check void option for PayWay partial captures."""
        super()._compute_void_remaining_amount()
        for wizard in self:
            # Check if ANY transaction is PayWay and it's a partial capture
            if (
                wizard.transaction_ids
                and any(tx.provider_code == 'aba_payway' for tx in wizard.transaction_ids)
                and wizard.has_remaining_amount
            ):
                # For PayWay, partial capture automatically voids the remainder
                wizard.void_remaining_amount = True

    @api.onchange('amount_to_capture')
    def _onchange_amount_to_capture_payway(self):
        """For PayWay partial captures, force void checkbox."""
        if (
            self.transaction_ids
            and any(tx.provider_code == 'aba_payway' for tx in self.transaction_ids)
            and self.amount_to_capture
            and self.amount_to_capture < self.available_amount
        ):
            self.void_remaining_amount = True

    @api.depends('transaction_ids', 'amount_to_capture', 'available_amount')
    def _compute_payway_auto_void(self):
        for wizard in self:
            wizard.payway_auto_void = (
                wizard.transaction_ids
                and any(tx.provider_code == 'aba_payway' for tx in wizard.transaction_ids)
                and wizard.amount_to_capture
                and wizard.amount_to_capture < wizard.available_amount
            )