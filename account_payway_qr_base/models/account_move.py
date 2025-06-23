from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    payway_qr_transaction_ids = fields.Many2many(
        'account_payway_qr_base.payway_qr.transaction'
    )
