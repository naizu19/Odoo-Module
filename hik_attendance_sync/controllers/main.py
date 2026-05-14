import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class HikWebhookController(http.Controller):

    @http.route('/hik/webhook', type='http', auth='none', methods=['POST'], csrf=False)
    def hik_webhook(self):
        """ Webhook endpoint for HikCentral real-time events. """
        try:
            # Type 'http' allows us to handle both flat JSON and JSON-RPC
            body = request.httprequest.data
            if not body:
                return request.make_response(json.dumps({'code': '0', 'msg': 'Empty Body'}), [('Content-Type', 'application/json')])
            
            data = json.loads(body)
            # Handle possible JSON-RPC envelope
            if 'params' in data:
                data = data['params']

            if not data:
                return request.make_response(json.dumps({'code': '0', 'msg': 'Connection Test Successful'}), [('Content-Type', 'application/json')])
            
            _logger.info("HikCentral Webhook received: %s", json.dumps(data))
            events = data.get('events', [])
            
            # Find active configuration to verify token and process events
            config = request.env['hik.config'].sudo().search([('is_active', '=', True)], limit=1)
            
            if config and config.webhook_token:
                received_token = request.httprequest.headers.get('token')
                if received_token != config.webhook_token:
                    _logger.warning("Invalid HikCentral webhook token received: %s", received_token)
                    return request.make_response(json.dumps({'code': '1', 'msg': 'Invalid Token'}), [('Content-Type', 'application/json')])

            if not config:
                _logger.warning("HikCentral Webhook: No active Hik configuration found.")
                return request.make_response(json.dumps({'code': '1', 'msg': 'Configuration missing'}), [('Content-Type', 'application/json')])

            if not events:
                return request.make_response(json.dumps({'code': '0', 'msg': 'Heartbeat/No Events'}), [('Content-Type', 'application/json')])

            # Process events
            count = config._process_hik_events(events)
            
            return request.make_response(json.dumps({'code': '0', 'msg': 'Processed %s events' % count}), [('Content-Type', 'application/json')])
        except Exception as e:
            _logger.exception("HikCentral Webhook Error: %s", str(e))
            return request.make_response(json.dumps({'code': '1', 'msg': str(e)}), [('Content-Type', 'application/json')])
