# Testing and production verification

## Repository tests

From the repository root, run:

```bash
python3 tests/run.py
git diff --check
```

The harness verifies protected dispatcher hashes, YAML syntax, collection locks and checksums, ordering, passive-only rendering, secret and proxy containment, firewall query semantics, PSK marker policy, and API create/update/refusal paths against a local fake Zabbix 8 JSON-RPC server.

These tests do not install packages or perform a live converge.

## Production qualification

Use an authorized disposable Rocky Linux 10 VM, never the controller. Complete all of these checks before relying on the role:

1. Run a clean first converge.
2. Run a second converge and require `changed=0`.
3. Require `systemctl is-active zabbix-agent2` to return `active`.
4. Inspect `ss -H -lntp` and require port `10050` on only the declared management address, owned by Agent 2.
5. Inspect both runtime and permanent firewalld state. Require only the declared Zabbix server `/32` rule for port `10050` and no broad service or port opening.
6. In Zabbix, verify exact host group, template, interface, tags, passive monitoring source, and PSK-only encryption.
7. Wait at least one normal sampling interval and confirm current `agent.ping` data and no persistent unsupported items.
8. Reboot the target and repeat service, socket, firewall, and data checks.
9. Exercise a deliberate PSK version rotation, then require a stable `changed=0` rerun.

If a converge fails after any mutation, treat the machine as partially changed. Read back network identity, fresh SSH access, firewall state, listeners, service state, and API state before resuming.
