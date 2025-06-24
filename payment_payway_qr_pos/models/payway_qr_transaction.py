from odoo import models
import logging


_logger = logging.getLogger(__name__)


class PaywayQRTransaction(models.Model):
    _inherit = "account_payway_qr_base.payway_qr.transaction"

    def _get_supported_models(self):
        return super()._get_supported_models() + ['pos.order']

    def _get_record(self):
        # Override
        # add it for pos.order
        if self.model == 'pos.order':
            logging.warm(f"{self.model}, {self.model_id}")
            return self.env[self.model].search([('uuid', '=', self.model_id)])
        return super()._get_record()
