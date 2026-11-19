# tuxbull.zabbix_agent

[![Role tests](https://github.com/Tuxbull-Open-Source/ansible.zabbix_agent/actions/workflows/tests.yml/badge.svg)](https://github.com/Tuxbull-Open-Source/ansible.zabbix_agent/actions/workflows/tests.yml)

Installs and securely onboards Zabbix Agent 2 on Rocky Linux 10. The role configures a passive-only, PSK-protected agent, restricts port `10050/tcp` to one Zabbix server, and registers the host through that server's local Zabbix API.

Existing `zabbix_onboarding_*` variable names are intentionally retained for compatibility.

## Which role do I need?

| Goal | Role |
| --- | --- |
| Build and configure a Zabbix server | `tuxbull.zabbix_server` |
| Install Agent 2 and register a monitored host | `tuxbull.zabbix_agent` (this role) |

## Requirements

- Ansible Core 2.15 or newer on the controller.
- A Rocky Linux 10 target with SELinux enforcing and `firewalld` already active.
- SSH and privilege escalation access to the target.
- An existing Zabbix 8.0 server that can reach the target management address.
- SSH access from the controller to the Zabbix server. API calls are delegated there and use its loopback endpoint.
- Existing `Linux servers` host group and `Linux by Zabbix agent` template.
- The pinned collections in `requirements.yml`.

Check mode is not supported. `zabbix_onboarding_validation_only: true` performs controller-only input validation without changing the target or Zabbix API.

## Installation

Create a requirements file or use [`examples/basic/requirements.yml`](examples/basic/requirements.yml):

```yaml
roles:
  - name: tuxbull.zabbix_agent
    src: https://github.com/Tuxbull-Open-Source/ansible.zabbix_agent.git
    scm: git
```

Then install the role and its pinned collections:

```bash
ansible-galaxy role install -r examples/basic/requirements.yml
ansible-galaxy collection install -r examples/basic/requirements.yml
```

## Required variables

| Variable | Meaning |
| --- | --- |
| `zabbix_onboarding_api_delegate` | Inventory hostname of the Zabbix server used for delegated loopback API calls |
| `zabbix_onboarding_api_password` | Zabbix API password; store it in Ansible Vault |
| `zabbix_onboarding_server_ip` | IPv4 address allowed to connect to Agent 2 |
| `zabbix_onboarding_management_ip` | Agent address assigned to the target and registered in Zabbix |
| `zabbix_onboarding_psk` | Unique per-host PSK: exactly 64 lowercase hexadecimal characters; store it in Ansible Vault |
| `zabbix_onboarding_psk_version` | Positive integer string; start with `"1"` and increment for every PSK or PSK-identity rotation |

See [`defaults/main.yml`](defaults/main.yml) for optional host identity, API
settings, package pins, and adoption controls. The host group and template names
are fixed for this validated role release.

## Minimal example

```yaml
# inventory.yml
all:
  children:
    zabbix_agents:
      hosts:
        app-01.example.test:
          ansible_host: 192.0.2.20
          zabbix_onboarding_api_delegate: zabbix-01.example.test
          zabbix_onboarding_server_ip: 192.0.2.10
          zabbix_onboarding_management_ip: 192.0.2.20
          zabbix_onboarding_psk_identity: zabbix-agent2-app-01
          zabbix_onboarding_psk_version: "1"
    zabbix_servers:
      hosts:
        zabbix-01.example.test:
          ansible_host: 192.0.2.10
```

```yaml
# playbook.yml
---
- name: Onboard Zabbix agents
  hosts: zabbix_agents
  gather_facts: true
  become: true
  roles:
    - role: tuxbull.zabbix_agent
```

Define `zabbix_onboarding_api_password` and `zabbix_onboarding_psk` in an encrypted vault. The complete runnable layout is in [`examples/basic/`](examples/basic/).

## Run and verify

From the example directory:

```bash
cp vault.example.yml vault.yml
ansible-vault encrypt vault.yml
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
```

The second run should report `changed=0`. Then verify the target and server:

```bash
ansible -i inventory.yml zabbix_agents -b -m ansible.builtin.command -a 'systemctl is-active zabbix-agent2'
ansible -i inventory.yml zabbix_agents -b -m ansible.builtin.command -a 'ss -H -lntp sport = :10050'
ansible -i inventory.yml zabbix_agents -b -m ansible.builtin.command -a 'firewall-cmd --list-rich-rules'
```

Confirm in the Zabbix UI that the host uses PSK-only encryption and receives fresh `agent.ping` data. See [Testing and verification](docs/testing.md) for the full production checklist.

## Add another monitored host

Copy the existing host entry under `zabbix_agents`, then change its SSH address,
management address, Zabbix host name, visible name, and PSK identity. Add the
host's PSK under its inventory name in `vault_zabbix_agent_psks`, then start its
PSK version at `"1"`.

Run only the new host first:

```bash
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass \
  --limit new-host.example.test
```

The `zabbix_servers` inventory group contains the existing Zabbix server used
for delegated API calls. Do not add the monitored host to that group.

## PSK version note

The Zabbix API cannot return a write-only PSK. The role therefore tracks its version and hash locally. Never change a PSK or its identity without incrementing `zabbix_onboarding_psk_version`; ambiguous or stale state fails closed. See [PSK lifecycle](docs/psk.md).

## Scope and limitations

- Supports Rocky Linux 10 only.
- Configures passive checks only; `ServerActive` is disabled.
- Manages one exact `/32` source rule for port `10050/tcp`; it refuses broad exposure.
- Requires an already-active firewall and existing Zabbix group/template objects.
- Does not install or configure the Zabbix server, DNS, routing, or controller credentials.
- Package versions are deliberately pinned and require a new audit before upgrades.

## Further documentation

- [Security model](docs/security.md)
- [API registration and ownership](docs/api.md)
- [PSK lifecycle and rotation](docs/psk.md)
- [Testing and production verification](docs/testing.md)
- [Upstream reuse and release audit](docs/REUSE-AUDIT.md)
- [Changelog](CHANGELOG.md)

Derived from template revision `479eda20a4317ca930de3b04b7d6c0fd87008951`. GPL-3.0-or-later.

## Project status

This is an independent community role and is not affiliated with or supported by
Zabbix LLC. Development was AI-assisted under maintainer review. Trust should be
based on the pinned dependencies, documented security boundaries, tests, and
your own environment validation.
