#!/usr/bin/env python3
import hashlib, json, os, pathlib, shutil, socket, subprocess, sys, tarfile, tempfile, time, yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTIFACT = pathlib.Path(os.environ.get('ZABBIX_AUDIT_DIR', 'tests/artifacts')) / 'community-zabbix-4.3.0.tar.gz'
PROTECTED_SHA256 = {
    'tasks/main.yml': '15be66db3da9d94d91278d3fa9096310df0b0089acb37409042ac58f7fc326b2',
    'tasks/include-file.yml': '37c6a2445cc7b3d164b6c848b9d7b249b01387a41711c21377cf60acedc143f4',
}

def require(value, message):
    if not value: raise AssertionError(message)
def text(path): return (ROOT / path).read_text()
def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]
def requests(log):
    if not log.exists(): return []
    return [json.loads(x) for x in log.read_text().splitlines() if x]
def methods(log): return [json.loads(x['body'])['method'] for x in requests(log)]
def start_api(port, state, log, capture=False):
    cmd=[sys.executable,str(ROOT/'tests/fake_zabbix_api.py'),'--port',str(port),'--state',str(state),'--log',str(log)]
    if capture: cmd.append('--proxy-capture')
    p=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
    for _ in range(50):
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1',port)) == 0: return p
        time.sleep(.05)
    raise AssertionError(p.stderr.read())

def listener_contract_harness():
    valid=('LISTEN 0 4096 192.0.2.20:10050 0.0.0.0:* '
           'users:(("zabbix_agent2",pid=1,fd=7))')
    invalid=(
        ['LISTEN 0 4096 0.0.0.0:9999 0.0.0.0:* users:(("zabbix_agent2",pid=1,fd=8))'],
        ['LISTEN 0 4096 [::]:9999 [::]:* users:(("zabbix_agent2",pid=1,fd=8))'],
        ['LISTEN 0 4096 1192.0.2.20:10050 0.0.0.0:* users:(("zabbix_agent2",pid=1,fd=7))'],
        ['LISTEN 0 4096 192.0.2.20:10051 0.0.0.0:* users:(("zabbix_agent2",pid=1,fd=7))'],
        ['LISTEN 0 4096 192.0.2.20:10050 0.0.0.0:* users:(("other",pid=1,fd=7))'],
        [valid,'LISTEN 0 4096 0.0.0.0:9999 0.0.0.0:* users:(("zabbix_agent2",pid=1,fd=8))'],
        [valid,valid.replace('pid=1','pid=2')],
    )
    assertions="""          - >-
            fixture |
            select('search', '\"zabbix_agent2\"') |
            select('match', '^LISTEN\\s+\\d+\\s+\\d+\\s+' ~
            (management_ip | regex_escape) ~ ':10050\\s+\\S+\\s+users:') |
            list | length == 1
          - >-
            fixture |
            select('search', '\"zabbix_agent2\"') | list | length == 1
"""
    with tempfile.TemporaryDirectory() as td:
        d=pathlib.Path(td); config=d/'ansible.cfg'
        config.write_text('[defaults]\nretry_files_enabled=False\n')
        env=os.environ.copy(); env['ANSIBLE_CONFIG']=str(config)
        cases=[('valid',[valid],True)]+[(f'invalid-{i}',v,False) for i,v in enumerate(invalid)]
        for name,fixture,expected in cases:
            play=d/f'{name}.yml'
            play.write_text('---\n- hosts: localhost\n  connection: local\n  gather_facts: false\n'
                            f'  vars:\n    management_ip: 192.0.2.20\n    fixture: {json.dumps(fixture)}\n'
                            '  tasks:\n    - ansible.builtin.assert:\n        that:\n'+assertions)
            result=subprocess.run(['ansible-playbook',str(play),'-i','localhost,'],cwd=d,env=env,
                                  text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            require((result.returncode==0)==expected,f'{name} listener result:\n{result.stdout}')

def api_play(path, port, marker, version='1', psk='a'*64, identity='zabbix-agent2-app-01',
             adopt=False, proxy=None, expect='none'):
    task_copy = path.with_name('register_verify_test.yml')
    task_copy.write_text(text('tasks/shared/30_register_verify.yml')
                         .replace('      become: true\n', '      become: false\n')
                         .replace('        owner: root\n', '')
                         .replace('        group: root\n', ''))
    marker_copy = path.with_name('marker_validation_test.yml')
    marker_tasks = text('tasks/shared/00_validate.yml').split(
        '- name: Inspect versioned PSK marker before any target mutation\n', 1)[1]
    marker_copy.write_text(('---\n- name: Inspect versioned PSK marker before any target mutation\n' + marker_tasks)
                           .replace('  become: true\n', '  become: false\n')
                           .replace("      - not _zabbix_onboarding_psk_marker_stat.stat.exists or _zabbix_onboarding_psk_marker_stat.stat.pw_name == 'root'\n", '')
                           .replace("      - not _zabbix_onboarding_psk_marker_stat.stat.exists or _zabbix_onboarding_psk_marker_stat.stat.gr_name == 'root'\n", ''))
    content=f'''---
- hosts: localhost
  gather_facts: false
  vars:
    zabbix_onboarding_api_url: http://127.0.0.1:{port}/api_jsonrpc.php
    zabbix_onboarding_api_user: Admin
    zabbix_onboarding_api_password: secret
    zabbix_onboarding_api_delegate: localhost
    zabbix_onboarding_host_name: app-01
    zabbix_onboarding_visible_name: app-01
    zabbix_onboarding_management_ip: 192.0.2.20
    zabbix_onboarding_psk_identity: {identity}
    zabbix_onboarding_psk: {psk}
    zabbix_onboarding_psk_version: "{version}"
    zabbix_onboarding_adopt_existing: {str(adopt).lower()}
    zabbix_onboarding_psk_marker_path: {marker}
    zabbix_onboarding_host_group: Linux servers
    zabbix_onboarding_template: Linux by Zabbix agent
    _zabbix_onboarding_managed_tag: managed-by
    _zabbix_onboarding_managed_tag_value: zabbix-agent-onboarding
    _zabbix_onboarding_psk_version_tag: zabbix-psk-version
  tasks:
    - ansible.builtin.include_tasks: {marker_copy}
    - ansible.builtin.include_tasks: {task_copy}
    - ansible.builtin.assert:
        that:
          - {str(expect != 'create').lower()} or _zabbix_onboarding_create is changed
          - {str(expect != 'update').lower()} or _zabbix_onboarding_update is changed
          - {str(expect != 'none').lower()} or _zabbix_onboarding_create is not changed
          - {str(expect != 'none').lower()} or _zabbix_onboarding_update is not changed
'''
    path.write_text(content)
    env=os.environ.copy()
    env.update({'HTTP_PROXY':proxy or '', 'HTTPS_PROXY':proxy or '', 'ALL_PROXY':proxy or '', 'NO_PROXY':''})
    return subprocess.run(['ansible-playbook',str(path),'-i','localhost,','-c','local'],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env)

# Parse all YAML and preserve protected template dispatcher bytes.
for p in ROOT.rglob('*.yml'):
    if 'collections' not in p.parts:
        list(yaml.safe_load_all(p.read_text()))
for rel in ('tasks/main.yml', 'tasks/include-file.yml'):
    require(hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == PROTECTED_SHA256[rel], f'{rel} changed')

numbered = sorted({p.name for p in (ROOT/'tasks').glob('*/*.yml') if p.name[:2].isdigit()})
require(numbered == ['00_validate.yml','10_firewall.yml','20_install_configure.yml','30_register_verify.yml'], numbered)
require((ROOT/'tasks/Rocky-10/10_firewall.yml').is_file() and (ROOT/'tasks/Rocky-10/20_install_configure.yml').is_file(), 'stage placement')

req = yaml.safe_load(text('requirements.yml'))['collections']
expected = {'community.zabbix':'4.3.0','ansible.windows':'3.3.0','ansible.netcommon':'8.4.0','ansible.utils':'6.0.1','ansible.posix':'2.1.0','community.general':'12.4.0','community.mysql':'4.1.0','community.postgresql':'4.2.0','community.windows':'3.1.0'}
require({x['name']:x['version'] for x in req} == expected, 'collection lock mismatch')
require(ARTIFACT.is_file(), 'run tests/bootstrap-audit-artifacts.sh before the test suite')
require(hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() == 'd30bbf022bc32bae89771f8d3611b31d9a524f5d384ff600067e7d0ba9480a5a', 'artifact checksum')
with tarfile.open(ARTIFACT) as t:
    agent = t.extractfile('roles/zabbix_agent/templates/agent.conf.j2').read().decode()
    configure = t.extractfile('roles/zabbix_agent/tasks/configure.yml').read().decode()
    selinux = t.extractfile('roles/zabbix_agent/tasks/selinux.yml').read().decode()
    redhat = t.extractfile('roles/zabbix_agent/vars/RedHat.yml').read().decode()
for token in ('ListenIP={{ zabbix_agent_listenip', 'Server={{ zabbix_agent_server', "ternary('', '# ') }}ServerActive=", 'TLSAccept={{ zabbix_agent_tlsaccept', 'TLSConnect={{ zabbix_agent_tlsconnect', 'TLSPSKFile={{ zabbix_agent_tlspskfile', 'TLSPSKIdentity={{ zabbix_agent_tlspskidentity'):
    require(token in agent, f'upstream template missing {token}')
require('mode: 0400' in configure and 'owner: zabbix' in configure, 'upstream PSK semantics')
require('selinux-policy-epel' in selinux, 'upstream EL10 defect changed')
require("zabbix-agent2', 'zabbix-agent') }}-{{ zabbix_agent_version }}.{{ zabbix_agent_version_minor }}" in redhat, 'package expression changed')

install = text('tasks/Rocky-10/20_install_configure.yml')
for token in ('community.zabbix.zabbix_repo','community.zabbix.zabbix_agent','apply:','no_log: true','diff: false','zabbix_agent_serveractive: null','zabbix_agent_statusport: null','zabbix_agent_tlsaccept: psk','zabbix_agent_tlsconnect: psk','zabbix_api_create_hosts: false','recursive=False','always:'):
    require(token in install, f'install contract missing {token}')
require('zabbix_agent_serveractive: "{{ zabbix_onboarding_server_ip }}"' not in install, 'active checks enabled')
rendered=[]
for line in agent.splitlines():
    if 'ServerActive=' in line: rendered.append('# ServerActive=')
    elif 'Server={{ zabbix_agent_server' in line: rendered.append('Server=192.0.2.10')
    elif 'ListenIP={{ zabbix_agent_listenip' in line: rendered.append('ListenIP=192.0.2.20')
    elif 'TLSAccept={{ zabbix_agent_tlsaccept' in line: rendered.append('TLSAccept=psk')
    elif 'TLSConnect={{ zabbix_agent_tlsconnect' in line: rendered.append('TLSConnect=psk')
require(rendered == ['ListenIP=192.0.2.20','Server=192.0.2.10','# ServerActive=','TLSAccept=psk','TLSConnect=psk'], rendered)

firewall = text('tasks/Rocky-10/10_firewall.yml')
for token in ("_zabbix_onboarding_broad_queries.rc != 1 or _zabbix_onboarding_broad_queries.stdout != 'no'",'--get-zone-of-interface=','ip, -j, address','--query-service=zabbix-agent','--query-port=10050/tcp','/32','--list-rich-rules','service name="zabbix-agent"','port port="10050"','_zabbix_onboarding_relevant_runtime_rules == [_zabbix_onboarding_rich_rule]','--permanent'):
    require(token in firewall, f'firewall contract missing {token}')
require('--add-service' not in firewall and '--add-port' not in firewall, 'broad firewall mutation')

for token in ('/etc/yum.repos.d/zabbix.repo','stable/rhel/10','RPM-GPG-KEY-ZABBIX-B5333005','zabbix-agent2-',"b5333005",'zabbix_onboarding_agent_evr','zabbix_agent2.conf','mode == \'0400\'','systemctl','unexpected non-management or auxiliary listener'):
    require(token in install, f'live verification contract missing {token}')
require('zabbix_onboarding_agent_evr: "2:8.0.0-release1.el10"' in text('defaults/main.yml'),
        'Agent2 EVR must include the audited RPM epoch')
live_rpm = 'zabbix-agent2-2:8.0.0-release1.el10|RSA/SHA512, Key ID d913219ab5333005'
require(live_rpm.startswith('zabbix-agent2-2:8.0.0-release1.el10|') and
        live_rpm.lower().endswith('b5333005'), 'epoch-bearing RPM fixture rejected')
listener_contract_harness()

api = text('tasks/shared/30_register_verify.yml')
require(api.count('use_proxy: false') == 6, 'every API request must bypass proxies')
for token in ('result.sessionid','selectHostGroups','Authorization: "Bearer','userData: true','host.create','host.update','user.logout','zabbix-psk-version','always:','failed_when: false'):
    require(token in api or token in text('vars/main.yml'), f'API contract missing {token}')
for forbidden in ('result.token','selectGroups','tls_psk_identity]'):
    require(forbidden not in api, f'forbidden API contract {forbidden}')
require('item.json.error' not in api, 'loop failed_when references item instead of registered result')

# Marker policy model rejects a changed secret without a version bump.
def marker_ok(marker, version, psk, identity):
    lines=dict(x.split('=',1) for x in marker.strip().splitlines())
    return (lines['version'] != version or
            (lines['sha256'] == hashlib.sha256(psk.encode()).hexdigest() and
             lines['identity_sha256'] == hashlib.sha256(identity.encode()).hexdigest()))
m=('version=1\nsha256='+hashlib.sha256(('a'*64).encode()).hexdigest()+'\nidentity_sha256='+
   hashlib.sha256(b'zabbix-agent2-app-01').hexdigest()+'\n')
require(marker_ok(m,'1','a'*64,'zabbix-agent2-app-01'), 'stable marker')
require(not marker_ok(m,'1','b'*64,'zabbix-agent2-app-01'), 'same-version secret change accepted')
require(not marker_ok(m,'1','a'*64,'changed-identity'), 'same-version identity change accepted')
require(marker_ok(m,'2','b'*64,'changed-identity'), 'rotation rejected')

# Exercise exact Ansible API tasks against an HTTP fake API.
with tempfile.TemporaryDirectory() as td:
    d=pathlib.Path(td); state=d/'state.json'; log=d/'api.log'; play=d/'api.yml'; marker=d/'psk-state'
    port=free_port(); server=start_api(port,state,log)
    try:
        r=api_play(play,port,marker,expect='create'); require(r.returncode==0,r.stdout)
        create_reqs=requests(log); require(methods(log).count('host.create')==1 and methods(log).count('host.update')==0, methods(log))
        create_body=next(json.loads(x['body']) for x in create_reqs if json.loads(x['body'])['method']=='host.create')
        require(create_body['params']['tls_psk']=='a'*64 and create_body['params']['tls_psk_identity']=='zabbix-agent2-app-01','create PSK')
        require(marker.stat().st_mode & 0o777 == 0o600, 'marker mode')
        require(marker.read_text() == m, repr(marker.read_text()))
        log.write_text(''); r=api_play(play,port,marker,expect='none'); require(r.returncode==0,r.stdout); require('host.update' not in methods(log), methods(log))
        log.write_text(''); r=api_play(play,port,marker,identity='changed-identity')
        require(r.returncode!=0, 'same-version identity change accepted')
        require('host.create' not in methods(log) and 'host.update' not in methods(log), methods(log))
        log.write_text(''); r=api_play(play,port,marker,version='2',identity='changed-identity',expect='update'); require(r.returncode==0,r.stdout)
        update=next(json.loads(x['body']) for x in requests(log) if json.loads(x['body'])['method']=='host.update')
        require(update['params']['tls_psk_identity']=='changed-identity','identity rotation omitted identity')
        s=json.loads(state.read_text()); s['host']['name']='drifted'; state.write_text(json.dumps(s)); log.write_text('')
        r=api_play(play,port,marker,version='2',identity='changed-identity',expect='update'); require(r.returncode==0,r.stdout)
        update=next(json.loads(x['body']) for x in requests(log) if json.loads(x['body'])['method']=='host.update')
        require('tls_psk' not in update['params'] and 'tls_psk_identity' not in update['params'],'readable drift resent PSK')
        # Simulate interrupted v2 API rotation while the durable marker remains at v1.
        marker.write_text(m); s=json.loads(state.read_text())
        for tag in s['host']['tags']:
            if tag['tag']=='zabbix-psk-version': tag['value']='2'
        state.write_text(json.dumps(s)); log.write_text('')
        r=api_play(play,port,marker,version='2',psk='b'*64)
        require(r.returncode!=0,'interrupted same-version managed host accepted stale marker')
        require('Bump zabbix_onboarding_psk_version to force a safe rotation' in r.stdout, r.stdout)
        require('host.update' not in methods(log), methods(log))
        log.write_text(''); r=api_play(play,port,marker,version='3',psk='c'*64,expect='update'); require(r.returncode==0,r.stdout)
        update=next(json.loads(x['body']) for x in requests(log) if json.loads(x['body'])['method']=='host.update')
        require(update['params']['tls_psk']=='c'*64,'bumped recovery omitted PSK')
        marker.unlink(); log.write_text('')
        r=api_play(play,port,marker,version='3',psk='c'*64)
        require(r.returncode!=0,'managed same-version host accepted absent marker')
        require('host.update' not in methods(log), methods(log))
        s=json.loads(state.read_text()); s['duplicate']=True; state.write_text(json.dumps(s)); log.write_text('')
        r=api_play(play,port,marker,version='3',psk='c'*64); require(r.returncode!=0,'duplicate accepted')
        s['duplicate']=False; s['host']['tags']=[]; state.write_text(json.dumps(s)); log.write_text('')
        r=api_play(play,port,marker,version='3',psk='c'*64); require(r.returncode!=0,'unowned accepted')
        log.write_text(''); r=api_play(play,port,marker,version='3',psk='c'*64,adopt=True,expect='update'); require(r.returncode==0,r.stdout)
        update=next(json.loads(x['body']) for x in requests(log) if json.loads(x['body'])['method']=='host.update')
        require('tls_psk' in update['params'],'adoption omitted PSK')
    finally:
        server.terminate(); server.wait()

# Hostile proxy must receive no delegated loopback API requests.
with tempfile.TemporaryDirectory() as td:
    d=pathlib.Path(td); state=d/'state.json'; direct=d/'direct.log'; capture=d/'proxy.log'; play=d/'api.yml'; marker=d/'psk-state'
    direct_port=free_port(); proxy_port=free_port(); direct_server=start_api(direct_port,state,direct); proxy_server=start_api(proxy_port,d/'pstate.json',capture,True)
    try:
        r=api_play(play,direct_port,marker,proxy=f'http://127.0.0.1:{proxy_port}',expect='create'); require(r.returncode==0,r.stdout)
        require(not capture.exists() or capture.read_text()=='','API request reached hostile proxy')
    finally:
        direct_server.terminate(); proxy_server.terminate(); direct_server.wait(); proxy_server.wait()

# Installed-role syntax and controller-only execution.
with tempfile.TemporaryDirectory() as td:
    h=pathlib.Path(td); (h/'roles').mkdir(); shutil.copytree(ROOT,h/'roles/tuxbull.zabbix_agent')
    (h/'ansible.cfg').write_text('[defaults]\nroles_path=roles\nretry_files_enabled=False\n')
    env=os.environ.copy()
    env.update({
        'PATH': str(pathlib.Path(shutil.which('ansible-playbook')).parent)+':/usr/bin:/bin',
        'HOME': str(h),
        'ANSIBLE_CONFIG': str(h/'ansible.cfg'),
        'ANSIBLE_COLLECTIONS_PATH': str(ROOT/'collections'),
        'PWD': str(h),
    })
    play=str(h/'roles/tuxbull.zabbix_agent/tests/test.yml')
    for extra in (['--syntax-check'],[]):
        result=subprocess.run(['ansible-playbook',play,'-i','localhost,','-c','local']+extra,cwd=h,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        require(result.returncode == 0, result.stdout)

print('PASS: role contracts, passive config, marker policy, fake API lifecycle, proxy isolation, and validation harness')
