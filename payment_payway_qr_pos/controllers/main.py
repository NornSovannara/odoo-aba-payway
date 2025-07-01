from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


class PayWayController(http.Controller):
    _webhook_url = '/pos/payway/webhook'

    @http.route(_webhook_url, type='http', auth='public', methods=['POST'], csrf=False)
    def payway_webhook(self, **data):

        # Search data
        # pos_order = (
        #     request.env['pos.order']
        #     .sudo()
        #     .search(
        #         [
        #             ('pos_reference', '=', 'Order 00167-009-0005'),
        #         ],
        #         limit=1,
        #     )
        # )
        print("Send notification from backend")
        # Call the method to send notification
        # pos_order.confirm_qr_payment()

        # Send notification from backend
        # channel_name = f'pos.order.payment.status.{"Order 00167-009-0005"}'
        channel_name = 'your_channel'
        bus_channel_tuple = (request.env.cr.dbname, channel_name)
        request.env['bus.bus']._sendone(
            bus_channel_tuple,
            'notification',
            {
                'pos_reference': "Order 00167-009-0005",
                'status': 'success',
                'message': 'QR Payment Successful!',
            },
        )

        request.env.cr.commit()
        return "OK"
