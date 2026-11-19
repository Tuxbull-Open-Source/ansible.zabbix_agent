# API registration and ownership

The controller does not need access to the Zabbix frontend. API work is delegated over SSH to `zabbix_onboarding_api_delegate` and sent to `zabbix_onboarding_api_url`, which defaults to the server-local endpoint `http://127.0.0.1:8080/api_jsonrpc.php`.

## Object resolution

The role requires exactly one matching host group and template. Defaults are:

- host group: `Linux servers`
- template: `Linux by Zabbix agent`

This validated release requires those exact names. Duplicate or missing matches
stop the run. Supporting different group or template names requires a separately
tested role change.

## Registration state

A new host is created with its group, template, interface, ownership tags, monitoring source, and PSK-only encryption in one request. Readable state is fetched and normalized after mutation.

Managed hosts carry these tags:

- `managed-by=zabbix-agent-onboarding`
- `zabbix-psk-version=<version>`

An existing host without the ownership tag is refused by default. Set `zabbix_onboarding_adopt_existing: true` only after reviewing the existing object; adoption may replace collection fields such as groups, templates, interfaces, and tags with the role's declared state.

## Idempotence and write-only fields

On stable reruns, the role compares readable state and sends updates only for drift. It does not resend the PSK when the version is unchanged. Because Zabbix does not expose PSKs on readback, local marker state governs safe rotation; see [PSK lifecycle and rotation](psk.md).

API logout runs in cleanup, and every secret-bearing request bypasses proxies and suppresses logs and diffs.
