import base64
import logging

from odoo.exceptions import UserError, ValidationError
from odoo import _, models, fields, api
from odoo.modules.module import get_module_resource
from odoo.tools import float_compare
from odoo.addons.aba_payway_qr_payment_pos_odoo import const


_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    image = fields.Image("Image", max_width=128, max_height=128)

    allow_qr_on_bill = fields.Boolean(
        string="Allow QR on Bill",
        help="If checked, a QR code for this payment method will be generated and printed on the customer bill.",
        default=False,
    )

    digital_qr_lifetime = fields.Integer(
        string="QR on screen expire time (minute)",
        related='journal_id.bank_account_id.digital_qr_lifetime',
        readonly=True,
    )

    bill_qr_lifetime = fields.Integer(
        string="QR on Bill expire time (Minute)",
        related='journal_id.bank_account_id.bill_qr_lifetime',
        readonly=True,
    )

    @api.onchange('qr_code_method')
    def _onchange_qr_code_method(self):
        for record in self:
            # Only auto-populate image/name for PayWay QR methods
            if record.qr_code_method not in const.PAYMENT_METHODS_CODES:
                continue
            
            if not record.name:
                method_name = const.QR_METHOD_NAME_MAP.get(record.qr_code_method)
                if method_name:
                    record.name = method_name

            image_filename = const.QR_METHOD_IMAGE_MAP.get(record.qr_code_method)
            if image_filename:
                image_path = get_module_resource(
                    'aba_payway_qr_payment_pos_odoo', 'static', 'src', 'img', image_filename,
                )
                if image_path:
                    with open(image_path, 'rb') as f:
                        record.image = base64.b64encode(f.read())

    
    def get_qr_code(self, amount, free_communication, structured_communication, currency, debtor_partner):
        self.ensure_one()

        if self.qr_code_method in const.PAYMENT_METHODS_CODES and amount is not False and float(amount) <= 0:
            return False

        if self.qr_code_method in const.PAYMENT_METHODS_CODES and amount == False:
            # Odoo attempt to call default qr generation with amount is False
            # which can be use when POS is offline
            # to prevent it return False when pos is offline
            return False

        if self.payment_method_type == 'qr_code' or self.qr_code_method in const.PAYMENT_METHODS_CODES:

            qr_type = self._context.get('qr_type')
            if qr_type == "bill" and (self.qr_code_method == const.PAYMENT_METHODS_MAPPING['abapay_khqr'] and not self.allow_qr_on_bill):
                return False

        if self.qr_code_method in const.PAYMENT_METHODS_CODES:
            # Pre-Validate amount and currency against server-side order data.
            # Raises if values don't match, blocking requests with tampered parameters.
            self._payway_validate_qr_params(amount, currency, free_communication)

        return super().get_qr_code(
            amount,
            free_communication,
            structured_communication,
            currency,
            debtor_partner,
        )

    def _payway_validate_qr_params(self, amount, currency_id, free_communication):
        """Pre-validate amount and currency before calling the PayWay API.
        """
        self.ensure_one()

        order = self._payway_get_order_by_reference(free_communication)
        if not order:
            raise UserError(_(
                "PayWay: Unable to validate order data on the server. "
                "Please sync and retry the payment."
            ))

        # === Currency check ===
        order_currency = order.currency_id
        client_currency = self.env['res.currency'].browse(currency_id)
        if not client_currency or client_currency.id != order_currency.id:
            _logger.warning(
                "PayWay QR: currency mismatch for order '%s' — client sent '%s', order is '%s'.",
                order.pos_reference,
                client_currency.name if client_currency else 'N/A',
                order_currency.name,
            )
            raise UserError(_(
                "PayWay: The payment currency (%(client_currency)s) does not match "
                "the order currency (%(order_currency)s). Please retry the payment.",
                client_currency=client_currency.name if client_currency else 'N/A',
                order_currency=order_currency.name,
            ))

        currency_name = (order_currency.name or '').upper()
        currency_precision = const.CURRENCY_DECIMALS.get(currency_name)
        precision_kwargs = (
            {'precision_digits': currency_precision}
            if currency_precision is not None
            else {'precision_rounding': order_currency.rounding}
        )

        # === Check 1: sum of all payment lines must cover Odoo-recomputed total ===
        # _compute_prices() uses Odoo's own tax engine on stored order lines,
        # handling discounts, loyalty rewards, and promotions correctly.
        # This detects tampering of both payment lines and QR amount.
        order._compute_prices()
        odoo_total = order.amount_total
        total_payments = sum(order.payment_ids.filtered(lambda p: p.amount > 0).mapped('amount'))
        if float_compare(total_payments, odoo_total, **precision_kwargs) < 0:
            _logger.warning(
                "PayWay QR: payment total mismatch for order '%s' — "
                "payment lines sum %s is less than Odoo-recomputed total %s.",
                order.pos_reference, total_payments, odoo_total,
            )
            raise UserError(_(
                "PayWay: The total payment amount (%(total_payments)s) does not cover "
                "the order total (%(odoo_total)s). Please retry the payment.",
                total_payments=total_payments,
                odoo_total=odoo_total,
            ))

        # === Check 2: QR amount must match the specific PayWay payment line ===
        # Catches attackers who tamper only the QR request without touching sync.
        # Also verifies the matched payment line belongs to a PayWay method —
        # qr_code_method is a server-stored field and cannot be forged via sync.
        client_amount = float(amount)
        qr_tran_id = self._context.get('qr_tran_id')
        payway_payment = order.payment_ids.filtered(
            lambda p: p.amount > 0
            and p.payment_method_id.id == self.id
            and p.payment_method_id.qr_code_method in const.PAYMENT_METHODS_CODES
            and (not qr_tran_id or p.transaction_id == qr_tran_id)
        )
        if not payway_payment:
            raise UserError(_(
                "PayWay: Unable to locate the PayWay payment line for this order. "
                "Please retry the payment."
            ))

        expected_amount = payway_payment[-1].amount
        if float_compare(client_amount, expected_amount, **precision_kwargs) != 0:
            _logger.warning(
                "PayWay QR: amount mismatch for order '%s' — client sent %s, payment line has %s.",
                order.pos_reference, client_amount, expected_amount,
            )
            raise UserError(_(
                "PayWay: The payment amount (%(client_amount)s) does not match "
                "the expected amount (%(server_amount)s). Please retry the payment.",
                client_amount=client_amount,
                server_amount=expected_amount,
            ))

    def _payway_get_order_by_reference(self, free_communication):
        """Look up a draft POS order from trusted context, then fallback to free_communication.

        free_communication format: "{name} {tracking_number}"
        Returns the pos.order record or empty recordset if not found.
        """
        order_uid = self._context.get('order_uid')
        if order_uid:
            order = self.env['pos.order'].sudo().search([
                ('uuid', '=', order_uid),
                ('state', '=', 'draft'),
            ], limit=1)
            if order:
                return order

        if not free_communication:
            return self.env['pos.order']

        # Split on last space: order name is everything except the last token (tracking_number)
        parts = free_communication.strip().rsplit(' ', 1)
        if len(parts) != 2:
            return self.env['pos.order']

        order_name = parts[0].strip()
        tracking_number = parts[1].strip()
        if not order_name:
            return self.env['pos.order']

        domain = [('name', '=', order_name), ('state', '=', 'draft')]
        try:
            domain.append(('tracking_number', '=', int(tracking_number)))
        except (TypeError, ValueError):
            pass
        return self.env['pos.order'].sudo().search(domain, limit=1)

    def payway_cancel_transaction(self, qr_tran_id):
        """Call res.partner.bank close payway transaction method"""

        self.ensure_one()
        if self.payment_method_type != 'qr_code' or not self.qr_code_method in const.PAYMENT_METHODS_CODES:
            return True            

        payment_bank = self.journal_id.bank_account_id
        payment_bank._payway_api_close_transaction(qr_tran_id)

    def payway_verify_transaction(
        self,
        qr_tran_id,
    ):
        self.ensure_one()
        if self.payment_method_type != 'qr_code' or not self.qr_code_method in const.PAYMENT_METHODS_CODES:
            return True

        payment_bank = self.journal_id.bank_account_id
        response = payment_bank._payway_api_check_transaction(qr_tran_id)
        
        is_payment_complete = str(response['data']['payment_status_code']) == '0'
        return is_payment_complete

    def payway_refund_transaction(self, qr_tran_id, refund_amount):
        self.ensure_one()
        if self.payment_method_type != 'qr_code' or self.qr_code_method not in const.PAYMENT_METHODS_CODES:
            return True

        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise UserError(_('Only Point of Sale users can process PayWay refunds.'))

        if not qr_tran_id:
            raise UserError(_('Missing source PayWay transaction id for the refund request.'))

        refund_amount = float(refund_amount or 0.0)
        if refund_amount <= 0:
            raise UserError(_('Refund amount must be greater than zero.'))

        payment_bank = self.journal_id.bank_account_id
        response = payment_bank._payway_api_refund_transaction(qr_tran_id, refund_amount)
        return str(response['status']['code']) == '00'

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)
        
        fields = ['qr_code_method', 'digital_qr_lifetime', 'bill_qr_lifetime', 'allow_qr_on_bill']
        for field in fields:
            if field not in res:
                res.append(field)        
        
        return res
