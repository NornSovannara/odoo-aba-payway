# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo import _, models, fields, api


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    # payway_provider_id = fields.Many2one(
    #     'payment.provider',
    #     string="Payway Payment Provider",
    #     help="The Payway payment provider configured for QR payments.",
    #     ondelete='restrict',
    # )

    # @api.model
    # def _get_qr_code_methods(self):
    #     return super()._get_qr_code_methods() + [('payway_qr', _('Payway QR'))]
