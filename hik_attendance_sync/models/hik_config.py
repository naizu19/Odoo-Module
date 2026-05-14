import hmac
import hashlib
import base64
import time
import uuid
import json
import logging
import urllib3
import requests
from datetime import datetime, timedelta, timezone
from odoo import models, fields, api, _
from odoo.exceptions import UserError

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_logger = logging.getLogger(__name__)

class HikConfig(models.Model):
    _name = 'hik.config'
    _description = 'HikCentral API Configuration'

    name = fields.Char(string="Configuration Name", default="Main Configuration", required=True)
    base_url = fields.Char(string='Base URL', help="e.g., https://192.168.1.100:443", required=True)
    app_key = fields.Char(string='App Key', required=True)
    app_secret = fields.Char(string='App Secret', required=True)
    door_index_codes = fields.Text(string='Door Index Codes', help="Comma-separated doorIndexCodes")
    last_sync_time = fields.Datetime(string='Last Sync Time')
    sync_interval = fields.Integer(string='Sync Interval (Minutes)', default=5)
    duplicate_threshold = fields.Integer(string='Duplicate Threshold (Seconds)', default=60)
    hik_user_id = fields.Char(string='HikCentral User ID', help="Optional: specific user to act as", default="odoo")
    webhook_token = fields.Char(string='Webhook Token', help="Security token sent in headers to verify authenticity", default=lambda self: self._default_webhook_token())

    def _default_webhook_token(self):
        import uuid
        return str(uuid.uuid4())
    is_active = fields.Boolean(string='Active', default=True)

    # Webhook / Subscription
    webhook_url = fields.Char(string='Webhook URL', help="e.g., https://yourdomain.com/hik/webhook")
    subscription_status = fields.Selection([
        ('unsubscribed', 'Unsubscribed'),
        ('active', 'Active'),
        ('error', 'Error'),
    ], string='Subscription Status', default='unsubscribed', readonly=True)

    # Event Types Selection (Updated for V3.0.1 codes)
    sync_face = fields.Boolean(string='Face Events (196893)', default=True)
    sync_fingerprint = fields.Boolean(string='Fingerprint Events (197127)', default=True)
    sync_card = fields.Boolean(string='Card Events (198914)', default=True)

    # --- API COMMONS ---
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('webhook_token'):
                vals['webhook_token'] = self._default_webhook_token()
        return super().create(vals_list)
    
    def write(self, vals):
        if 'webhook_token' in vals and not vals['webhook_token']:
            vals['webhook_token'] = self._default_webhook_token()
        return super().write(vals)
    
    def _get_signature(self, method, url_path, headers):
        """ Calculates HikCentral Professional OpenAPI signature. """
        lines = [
            method.upper(),
            headers.get('Accept', ''),
            headers.get('Content-Type', '')
        ]
        # Custom headers (x-ca- and userId) - sorted
        custom_headers = {k.lower(): v for k, v in headers.items() if (k.lower().startswith('x-ca-') or k.lower() == 'userid')}
        signed_header_keys = sorted(custom_headers.keys())
        
        for k in signed_header_keys:
            lines.append(f"{k}:{custom_headers[k]}")
        
        lines.append(url_path)
        sign_str = "\n".join(lines)

        signature = hmac.new(
            self.app_secret.encode('utf-8'),
            sign_str.encode('utf-8'),
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode('utf-8'), ",".join(signed_header_keys)

    def _call_hik_api(self, url_path, payload):
        """ Reliable wrapper for all HikCentral API requests. """
        full_url = self.base_url.rstrip('/') + url_path
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "X-Ca-Key": self.app_key,
            "X-Ca-Timestamp": str(int(time.time() * 1000)),
            "X-Ca-Nonce": str(uuid.uuid4()),
        }
        if self.hik_user_id:
            headers["userId"] = self.hik_user_id
        
        signature, signed_headers = self._get_signature("POST", url_path, headers)
        headers["X-Ca-Signature"] = signature
        headers["X-Ca-Signature-Headers"] = signed_headers

        start_time = time.time()
        payload_json = json.dumps(payload)
        
        try:
            # Using tuple timeout: (connect_timeout, read_timeout)
            response = requests.post(full_url, data=payload_json, headers=headers, timeout=(15, 60), verify=False)
            elapsed = (time.time() - start_time) * 1000
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != '0':
                return {
                    'error': True, 
                    'msg': data.get('msg', 'Unknown Error'), 
                    'data': data,
                    'execution_time': elapsed,
                    'payload': payload_json
                }
            
            return {
                'error': False, 
                'data': data.get('data', {}),
                'execution_time': elapsed,
                'payload': payload_json,
                'response': json.dumps(data)
            }
        except requests.exceptions.ConnectTimeout:
            return {'error': True, 'msg': _("Connection to %s timed out. Check your firewall/network.") % self.base_url, 'execution_time': (time.time() - start_time) * 1000}
        except requests.exceptions.ReadTimeout:
            return {'error': True, 'msg': _("Server at %s is responding too slowly.") % self.base_url, 'execution_time': (time.time() - start_time) * 1000}
        except requests.exceptions.ConnectionError:
            return {'error': True, 'msg': _("Connection error to %s. The server might be down or URL is wrong.") % self.base_url, 'execution_time': (time.time() - start_time) * 1000}
        except requests.exceptions.HTTPError as e:
            return {'error': True, 'msg': _("HTTP Error: %s") % str(e), 'execution_time': (time.time() - start_time) * 1000}
        except Exception as e:
            return {'error': True, 'msg': _("Request Exception: %s") % str(e), 'execution_time': (time.time() - start_time) * 1000}

    # --- CORE SYNC LOGIC ---

    def action_sync_attendance(self):
        """ Manual sync trigger following V3.0.1 Guide parameters. """
        for config in self:
            end_time = datetime.now(timezone.utc)
            start_time = config.last_sync_time
            if not start_time:
                start_time = end_time - timedelta(days=5) # Last 5 days if never synced
            else:
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
            
            # Format times for API
            start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S+00:00')
            end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S+00:00')

            # Event Types Selection following V3.0.1 guide
            event_type_selection = []
            if config.sync_face: event_type_selection.append(196893)
            if config.sync_fingerprint: event_type_selection.append(197127)
            if config.sync_card: event_type_selection.append(198914)

            if not event_type_selection:
                raise UserError(_("Please select at least one event type under Sync Control."))

            total_events_found = 0
            total_created = 0
            
            door_codes = [c.strip() for c in (config.door_index_codes or "").split(',') if c.strip()]
            if not door_codes:
                door_codes = config._get_all_door_codes()
                if door_codes:
                    config.sudo().write({'door_index_codes': ", ".join(door_codes)})
            
            # Fetch Person Mapping (systemId -> personCode) to correctly map events to employees
            person_map = config._get_person_mapping()

            for etype in event_type_selection:
                page_no = 1
                page_size = 500
                
                while True:
                    payload = {
                        "startTime": start_str,
                        "endTime": end_str,
                        "eventType": etype,
                        "pageNo": page_no, 
                        "pageSize": page_size,
                    }
                    if door_codes:
                        # Fixed: sending as array vs comma-separated string
                        # Usually it is an array, but some versions expect it as string.
                        payload["doorIndexCodes"] = ",".join(door_codes) if len(door_codes) > 1 else door_codes[0]

                    result = config._call_hik_api("/artemis/api/acs/v1/door/events", payload)
                    if result['error'] and 'parameter' in result['msg'].lower() and door_codes:
                        # Fallback: try as an array
                        payload["doorIndexCodes"] = door_codes
                        result = config._call_hik_api("/artemis/api/acs/v1/door/events", payload)
                        if result['error'] and 'parameter' in result['msg'].lower():
                            # Fallback 2: try skipping doorIndexCodes entirely to fetch all door events
                            payload.pop("doorIndexCodes", None)
                            result = config._call_hik_api("/artemis/api/acs/v1/door/events", payload)

                    if result['error']:
                        config._log_sync_error(result['msg'], result.get('data'), execution_time=result.get('execution_time'), payload=result.get('payload'))
                        break

                    events = result['data'].get('list', [])
                    current_page_count = len(events)
                    total_events_found += current_page_count
                    
                    created_in_page = config.sudo()._process_hik_events(events, person_map=person_map)
                    total_created += created_in_page
                    
                    if current_page_count < page_size:
                        break
                    page_no += 1

            config.sudo().write({'last_sync_time': end_time.replace(tzinfo=None)})
            if total_events_found > 0 or total_created > 0:
                self.env['hik.sync.log'].create({
                    'name': _("Attendance Sync Successful"),
                    'status': 'success',
                    'events_found': total_events_found,
                    'attendance_created': total_created,
                    'message': _("Processed %s events. Created %s attendances.") % (total_events_found, total_created)
                })

    def _process_hik_events(self, events, person_map=None):
        """ Processes raw events with deduplication. Mapping systemId -> employee_no. """
        if not events: return 0
        events.sort(key=lambda x: x.get('eventTime', ''))
        
        # If person_map is not provided (e.g. from webhook), fetch it once
        if person_map is None:
            person_map = self._get_person_mapping()

        person_codes = set()
        event_ids = set()
        for e in events:
            system_id = e.get('personId')
            pcode = person_map.get(system_id) or e.get('personCode')
            eid = e.get('eventId')
            if pcode: 
                person_codes.add(str(pcode))
                e['_odoo_person_code'] = str(pcode) # Cache for later
            if eid: event_ids.add(eid)
        
        if not person_codes: return 0
        existing_eids = set(self.env['hik.event'].search([('event_id', 'in', list(event_ids))]).mapped('event_id'))
        employees = self.env['hr.employee'].search([('employee_no', 'in', list(person_codes))])
        if not employees: return 0

        emp_map = {emp.employee_no: emp for emp in employees if emp.employee_no}
        employee_ids = employees.ids
        open_att_map = {att.employee_id.id: att for att in self.env['hr.attendance'].search([
            ('employee_id', 'in', employee_ids), ('check_out', '=', False)
        ])}

        last_event_map = {}
        last_atts = self.env['hr.attendance'].search([('employee_id', 'in', employee_ids)], order='check_in desc')
        for att in last_atts:
            if att.employee_id.id not in last_event_map:
                last_event_map[att.employee_id.id] = att.check_out or att.check_in

        count = 0
        for event in events:
            eid = event.get('eventId')
            if eid in existing_eids: continue
            
            pcode = event.get('_odoo_person_code')
            employee = emp_map.get(pcode)
            if not employee: continue

            event_time = self._parse_hik_time(event.get('eventTime'))
            if not event_time: continue

            emp_id = employee.id
            door_name = event.get('doorName') or event.get('doorIndexCode') or 'Unknown'
            
            self.env['hik.event'].create({
                'event_id': eid,
                'event_time': event_time,
                'employee_no': pcode,
                'door_name': door_name,
                'event_type': int(event.get('eventType', 0)),
                'processed': True,
            })
            existing_eids.add(eid)

            last_time = last_event_map.get(emp_id)
            if last_time and abs((event_time - last_time).total_seconds()) < self.duplicate_threshold:
                continue

            open_att = open_att_map.get(emp_id)
            try:
                if open_att:
                    if event_time > open_att.check_in:
                        open_att.write({'check_out': event_time, 'check_out_device': f"{door_name} (Out)"})
                        last_event_map[emp_id] = event_time
                        open_att_map.pop(emp_id, None)
                        count += 1
                else:
                    new_att = self.env['hr.attendance'].create({
                        'employee_id': emp_id, 
                        'check_in': event_time,
                        'check_in_device': f"{door_name} (In)"
                    })
                    last_event_map[emp_id] = event_time
                    open_att_map[emp_id] = new_att
                    count += 1
            except Exception as e:
                _logger.warning("HikCentral: Attendance error for %s: %s", employee.name, str(e))
                continue
        return count

    def _log_sync_info(self, title, message):
        self.env['hik.sync.log'].create({'name': title, 'status': 'success', 'message': message})

    def action_subscribe_events(self):
        """ Subscribe per HikCentral OpenAPI Guide. """
        for config in self:
            if not config.webhook_url:
                raise UserError(_("Please provide a Webhook URL first."))
            
            event_types = []
            if config.sync_face:
                event_types.extend([196893, 196888, 196890, 196891, 196892, 196896]) 
            if config.sync_fingerprint:
                event_types.extend([197127, 196885, 196886, 196887, 196894, 196895]) 
            if config.sync_card:
                event_types.extend([198914, 198915, 110025]) 

            if not event_types:
                raise UserError(_("Please select at least one event type to sync."))

            payload = {
                "eventTypes": list(set(event_types)),
                "eventDest": config.webhook_url,
                "token": config.webhook_token,
                "passBack": 1,
                "subType": 2, 
                "eventLevel": [0, 1, 2],
            }

            result = config._call_hik_api("/artemis/api/eventService/v1/eventSubscriptionByEventTypes", payload)
            if result['error']:
                config.subscription_status = 'error'
                raise UserError(_("Subscription failed: %s") % result.get('msg', 'Unknown Error'))
            
            config.subscription_status = 'active'
            config._log_sync_info(_("Webhook Subscribed"), _("Subscribed successfully to %s") % event_types)

    def action_unsubscribe_events(self):
        """ Unsubscribe from events. """
        for config in self:
            event_types = [196893, 197127, 198914]
            result = config._call_hik_api("/artemis/api/eventService/v1/eventUnSubscriptionByEventTypes", {"eventTypes": event_types})
            if result['error']:
                raise UserError(_("Unsubscription failed: %s") % result['msg'])
            
            config.subscription_status = 'unsubscribed'
            config._log_sync_info(_("Webhook Unsubscribed"), _("Unsubscription successful."))


    def _parse_hik_time(self, time_str):
        if not time_str: return None
        try:
            # Guide shows '2018-08-10 20:00:00' in examples, but ISO in parameters.
            # Handle both formats.
            if 'T' in time_str:
                dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            else:
                dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            
            return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt
        except: return None

    def _log_sync_error(self, message, details=None, execution_time=0, payload=None):
        self.env['hik.sync.log'].create({
            'name': _("Sync Error"), 'status': 'error',
            'message': message, 
            'error_details': json.dumps(details) if details else message,
            'request_payload': payload,
            'execution_time': execution_time
        })

    def _get_person_mapping(self):
        """ Returns a dictionary mapping HikCentral system personId to personCode. """
        self.ensure_one()
        mapping = {}
        page = 1
        while True:
            res = self._call_hik_api("/artemis/api/resource/v1/person/personList", {"pageNo": page, "pageSize": 500})
            if res['error']: break
            data = res['data'].get('list', [])
            if not data: break
            for p in data:
                sid = p.get('personId')
                code = p.get('personCode')
                if sid and code:
                    mapping[str(sid)] = str(code)
            if len(data) < 500: break
            page += 1
        return mapping

    def _get_all_door_codes(self):
        """ Helper to fetch all available door index codes from all regions. """
        self.ensure_one()
        door_codes = []
        # 1. Fetch Regions
        resp_regions = self._call_hik_api("/artemis/api/resource/v1/regions", {"pageNo": 1, "pageSize": 500})
        if not resp_regions['error']:
            regions = resp_regions['data'].get('list', [])
            for region in regions:
                r_code = str(region.get('indexCode') or region.get('regionIndexCode'))
                # 2. Fetch Doors for each region
                res_doors = self._call_hik_api("/artemis/api/resource/v1/acsDoor/region/acsDoorList", {
                    "regionIndexCode": r_code, "pageNo": 1, "pageSize": 500
                })
                if not res_doors['error']:
                    for d in res_doors['data'].get('list', []):
                        d_code = d.get('doorIndexCode')
                        if d_code:
                            door_codes.append(str(d_code))
        return list(set(door_codes)) # Unique codes


    def _cron_cleanup_logs(self, days=30):
        cutoff_date = datetime.now() - timedelta(days=days)
        old_logs = self.env['hik.sync.log'].search([('status', '=', 'success'), ('create_date', '<', cutoff_date)])
        if old_logs:
            old_logs.unlink()
            _logger.info("HikCentral: Cleaned up %d old sync logs." % len(old_logs))
