# Security model

The role is fail-closed: it validates the target, firewall, secrets metadata, package identity, and API objects before accepting a deployment as complete.

## Network boundary

`firewalld` must already be active. Before package installation can start Agent 2, the role rejects broad `zabbix-agent` service and `10050/tcp` openings and adds one runtime and permanent rich rule for `zabbix_onboarding_server_ip/32`. It verifies that `zabbix_onboarding_management_ip` belongs to the target and configures the agent to listen there.

Agent 2 is passive-only. `ServerActive` is disabled, and both agent acceptance and API host encryption are PSK-only.

## Secret handling

Keep `zabbix_onboarding_api_password` and each host's `zabbix_onboarding_psk` in an encrypted vault. Secret-bearing task blocks use `no_log: true` and `diff: false`. Delegated API requests set `use_proxy: false`, so target proxy environment variables cannot redirect loopback credentials.

Use a unique 64-character lowercase hexadecimal PSK for every host. Do not put production secrets, addresses, or hostnames in this repository.

## Package and platform boundary

The role supports SELinux-enforcing Rocky Linux 10. It delegates repository, package, Agent 2 configuration, PSK-file permissions, service, and handlers to pinned `community.zabbix` roles. A narrow local adapter supplies audited EL10 SELinux policy dependencies missing from the pinned upstream path. Package EVRs and signing-key identities are checked explicitly.

The role rejects check mode because its composed installer and readiness checks are not check-mode safe. Use validation-only mode for non-mutating input checks.

## Operational expectations

Before production use, test against a disposable Rocky Linux 10 VM. Confirm exact listener ownership, firewall runtime and permanent state, encrypted polling, idempotence, and reboot persistence. See [Testing and production verification](testing.md).
