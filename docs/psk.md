# PSK lifecycle and rotation

Zabbix PSKs are write-only API state. The role binds each managed host to:

- `zabbix_onboarding_psk_version`
- a hash of `zabbix_onboarding_psk`
- a hash of `zabbix_onboarding_psk_identity`

The target stores this evidence in a root-only marker at `zabbix_onboarding_psk_marker_path`.

## First onboarding

Start with a positive integer string, normally:

```yaml
zabbix_onboarding_psk_version: "1"
```

After registration and exact API readback, the role writes the marker. The plaintext PSK is not stored in the marker.

## Stable reruns

With the same version, secret, and identity, the role does not resend the write-only PSK. A same-version change to the PSK or identity is refused.

## Rotation

1. Generate a new unique 64-character lowercase hexadecimal PSK.
2. Optionally change `zabbix_onboarding_psk_identity`.
3. Increment `zabbix_onboarding_psk_version` by one.
4. Update the encrypted vault.
5. Run the playbook and verify encrypted agent communication.
6. Run it again and require `changed=0`.

The role sends PSK fields during the version change and records the new marker only after verification.

## Ambiguous recovery

If the Zabbix host already advertises the requested version but the local marker is missing or stale, the role cannot prove that the supplied PSK equals the API's write-only value. It refuses recovery at that version. Increment the version and rotate the PSK rather than recreating a marker manually.
