# Tests

Run:

```bash
tests/bootstrap-audit-artifacts.sh
python3 tests/run.py
```

The bootstrap script downloads `community.zabbix` 4.3.0 and verifies its exact
SHA-256 before the tests inspect it. Downloaded files stay under ignored
`tests/artifacts/`.

The suite verifies template hashes, YAML syntax, the complete
collection lock/checksums, stage ordering, passive-only upstream config rendering,
secret/proxy containment, firewall negative semantics, PSK marker version policy,
and executes the real API task file against a localhost fake Zabbix 8 JSON-RPC
server for create, no-update rerun, readable drift without PSK, version rotation
with PSK, adoption, duplicate/unowned refusal, and hostile-proxy isolation.

No live converge is performed by this repository test. Before production use,
run an authorized clean Rocky 10 VM converge, a second `changed=0` converge,
reboot persistence, Agent2 listener/config tests, Zabbix API readback, and routing
from the real Zabbix server. Never test package mutation on the controller.
