# Basic example

This example onboards `app-01.example.test` through `zabbix-01.example.test`. All names and addresses are documentation-only; replace them with private inventory values before use.

## Prepare

```bash
ansible-galaxy role install -r requirements.yml
ansible-galaxy collection install -r requirements.yml
cp vault.example.yml vault.yml
```

Edit `vault.yml`. Set the API password and replace each host's placeholder with
a unique PSK containing exactly 64 lowercase hexadecimal characters. The map key
must match the host's inventory name. Then encrypt the file:

```bash
ansible-vault encrypt vault.yml
```

Update `inventory.yml` with the real SSH targets, Zabbix server address, target management address, API delegate, host name, PSK identity, and PSK version. The Zabbix server inventory host must be reachable by SSH from the controller.

## Run

```bash
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
ansible-playbook -i inventory.yml playbook.yml --ask-vault-pass
```

The second run should report `changed=0`.

## Add another monitored host

Copy `app-01.example.test` under `zabbix_agents` in `inventory.yml`. Give the new
host its own address, Zabbix host name, visible name, and PSK identity. Add a
matching key and unique PSK under `vault_zabbix_agent_psks` in `vault.yml`.
Start `zabbix_onboarding_psk_version` at `"1"`, then test only that host with
`--limit` before running the play for the full group.

## Verify

```bash
ansible -i inventory.yml zabbix_agents -b -m ansible.builtin.command -a 'systemctl is-active zabbix-agent2'
ansible -i inventory.yml zabbix_agents -b -m ansible.builtin.command -a 'ss -H -lntp sport = :10050'
ansible -i inventory.yml zabbix_agents -b -m ansible.builtin.command -a 'firewall-cmd --list-rich-rules'
```

Require an active service, a listener only on the declared management address, and one source `/32` rule for the declared Zabbix server. In the Zabbix UI, confirm PSK-only encryption and fresh `agent.ping` data.

`vault.yml` is intentionally not included. Keep it out of version control. To rotate a PSK or identity, update the encrypted value and increment `zabbix_onboarding_psk_version` together.
