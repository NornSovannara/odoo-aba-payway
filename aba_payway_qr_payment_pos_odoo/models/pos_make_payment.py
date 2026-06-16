from odoo import api, fields, models

from odoo.addons.aba_payway_qr_payment_pos_odoo import const


class PosMakePayment(models.TransientModel):
    _inherit = 'pos.make.payment'

    is_payway_refund = fields.Boolean(
        compute='_compute_is_payway_refund',
        help="True when the selected payment method is PayWay and the amount is negative (refund).",
    )

    @api.depends('payment_method_id', 'amount')
    def _compute_is_payway_refund(self):
        for rec in self:
            rec.is_payway_refund = (
                rec.amount < 0
                and rec.payment_method_id.qr_code_method in const.PAYMENT_METHODS_CODES
            )
