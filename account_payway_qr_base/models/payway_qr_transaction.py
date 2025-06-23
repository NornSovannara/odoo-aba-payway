from odoo import api, fields, models, _


class PaywayQRTransaction(models.Model):
    _name = "account_payway_qr_base.payway_qr.transaction"
    _description = "Record of Payway QR transactions"

    # Model Field
    bank_id = fields.Many2one(
        "res.partner.bank",
        help="Bank used to generate the current Payway QR transaction",
    )

    # payment in respond to which model
    # Buinsess document that this qr support
    # ex: pos.order: Point of sale order
    model = fields.Char(string="Model")
    model_id = fields.Char(string="Model ID")

    qr_tran_id = fields.Char(readonly=True)
    qr_amount = fields.Char(readonly=True)
    qr_creation_datetime = fields.Datetime(readonly=True)
    qr_req_time = fields.Char(readonly=True)
    qr_currency = fields.Char(readonly=True)
    qr_payment_option = fields.Char(readonly=True)

    def _get_supported_models(self):
        return []
