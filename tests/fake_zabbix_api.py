#!/usr/bin/env python3
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

P = argparse.ArgumentParser()
P.add_argument('--port', type=int, required=True)
P.add_argument('--state', type=Path, required=True)
P.add_argument('--log', type=Path, required=True)
P.add_argument('--proxy-capture', action='store_true')
A = P.parse_args()


def load():
    if not A.state.exists():
        return {'host': None, 'duplicate': False, 'nextid': 10001}
    return json.loads(A.state.read_text())


def save(state):
    A.state.write_text(json.dumps(state, sort_keys=True))


def public_host(host):
    if host is None:
        return None
    result = {k: v for k, v in host.items() if k not in ('tls_psk', 'tls_psk_identity', 'groups', 'templates')}
    result['hostgroups'] = [{'groupid': str(x['groupid']), 'name': 'Linux servers'} for x in host.get('groups', [])]
    result['parentTemplates'] = [{'templateid': str(x['templateid']), 'host': 'Linux by Zabbix agent'} for x in host.get('templates', [])]
    result['interfaces'] = [dict({'interfaceid': str(20000 + i)}, **{k: (str(v) if k in ('type', 'main', 'useip', 'port') else v) for k, v in x.items()}) for i, x in enumerate(host.get('interfaces', []))]
    for key in ('hostid', 'status', 'monitored_by', 'tls_accept', 'tls_connect'):
        if key in result:
            result[key] = str(result[key])
    return result


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        with A.log.open('a') as f:
            f.write(json.dumps({'path': self.path, 'headers': dict(self.headers), 'body': raw.decode(errors='replace')}) + '\n')
        if A.proxy_capture:
            self.send_response(502); self.end_headers(); return
        try:
            req = json.loads(raw)
            state = load()
            method = req['method']
            params = req.get('params', {})
            if req.get('jsonrpc') != '2.0':
                raise ValueError('bad jsonrpc')
            if method == 'user.login':
                if params != {'username': 'Admin', 'password': 'secret', 'userData': True}:
                    raise ValueError('bad login params')
                result = {'sessionid': 'fake-session', 'userid': '1'}
            else:
                if self.headers.get('Authorization') != 'Bearer fake-session':
                    raise ValueError('bad authorization')
                if method == 'template.get':
                    result = [{'templateid': '10001', 'host': 'Linux by Zabbix agent'}]
                elif method == 'hostgroup.get':
                    result = [{'groupid': '2', 'name': 'Linux servers'}]
                elif method == 'host.get':
                    h = public_host(state['host'])
                    result = ([] if h is None else [h, dict(h, hostid='99999')] if state.get('duplicate') else [h])
                elif method == 'host.create':
                    host = dict(params)
                    host['hostid'] = str(state['nextid'])
                    state['nextid'] += 1
                    state['host'] = host
                    save(state)
                    result = {'hostids': [host['hostid']]}
                elif method == 'host.update':
                    if state['host'] is None or str(params.get('hostid')) != str(state['host']['hostid']):
                        raise ValueError('bad hostid')
                    state['host'].update(params)
                    save(state)
                    result = {'hostids': [str(state['host']['hostid'])]}
                elif method == 'user.logout':
                    result = True
                else:
                    raise ValueError('unsupported method ' + method)
            response = {'jsonrpc': '2.0', 'result': result, 'id': req.get('id')}
        except Exception as exc:
            response = {'jsonrpc': '2.0', 'error': {'code': -32602, 'message': str(exc)}, 'id': (req.get('id') if 'req' in locals() else None)}
        data = json.dumps(response).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


ThreadingHTTPServer(('127.0.0.1', A.port), Handler).serve_forever()
