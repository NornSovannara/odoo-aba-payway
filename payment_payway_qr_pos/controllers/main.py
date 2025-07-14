from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


class PayWayController(http.Controller):
    _webhook_url = '/pos/payway/webhook'

    @http.route(_webhook_url, type='json', auth='public', methods=['POST'], csrf=False)
    def payway_webhook(self):

        # Search data
        # pos_order = (request.env['pos.order'].sudo().search([('pos_reference', '=', 'Order 00167-009-0005'),],limit=1))
        # pos_order.confirm_qr_payment()

        print("Send notification from backend")
        data = request.get_json_data()
        channel_name = 'pos.order.payment.payway.' + data['tran_id']

        # Send notification from backend
        request.env['bus.bus'].sudo()._sendone(
            channel_name,
            'notification',
            data,
        )

        return "OK"
