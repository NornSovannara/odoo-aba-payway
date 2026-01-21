import logging
import pprint

from odoo import http
from odoo.http import request


_logger = logging.getLogger(__name__)

class PayWayController(http.Controller):
    _webhook_url = '/pos/payway/webhook'

    @http.route(_webhook_url, type='json', auth='public', methods=['POST'], csrf=False)
    def payway_webhook(self):

        try:
            data = request.get_json_data()
            _logger.info("Notification received from PayWay with data:\n%s", pprint.pformat(data))        
            channel_name = 'pos.order.payment.payway.' + data['tran_id']
            
            # TODO: Verify webhook signature
            # request.env['res.partner.bank'].sudo().with_context(active_test=False).search([
            #     'xyz'='abc'
            # ]).payway_key

            # Send notification from backend
            request.env['bus.bus'].sudo()._sendone(
                channel_name,
                'notification',
                {
                    **data,
                    "channel_name": channel_name
                },  
            )

        except Exception:
            _logger.exception("Unable to handle the webhook data.")

        return "OK"
