# Reuse and release audit

The source template is
[`Tuxbull-Open-Source/ansible.template`](https://github.com/Tuxbull-Open-Source/ansible.template)
revision `479eda20a4317ca930de3b04b7d6c0fd87008951`. `tasks/main.yml` SHA-256 is
`15be66db3da9d94d91278d3fa9096310df0b0089acb37409042ac58f7fc326b2` and
`tasks/include-file.yml` SHA-256 is
`37c6a2445cc7b3d164b6c848b9d7b249b01387a41711c21377cf60acedc143f4`.

The installer/configuration boundary is `community.zabbix` 4.3.0, Galaxy artifact
`community-zabbix-4.3.0.tar.gz`, SHA-256
`d30bbf022bc32bae89771f8d3611b31d9a524f5d384ff600067e7d0ba9480a5a`, tag
commit `3d6c7738b2bea9f575982f540e1907c4fe732dd2`. Its released RedHat vars prove
`zabbix-agent2-8.0.<release>` package composition; its template consumes
ListenIP, Server, ServerActive, TLSAccept, TLSConnect, TLSPSKFile and
TLSPSKIdentity. Its PSK task writes the supplied secret as user `zabbix`, mode
0400. The wrapper invokes it under `include_role.apply` with `no_log` and
`diff: false`, and disables its unrelated legacy API path.

The released EL10 path incorrectly requests nonexistent `selinux-policy-epel`.
The narrow local adapter reuses `community.zabbix.zabbix_repo`, then resolves,
installs, and verifies the proven replacements:

- `selinux-policy-targeted-extra-42.1.27-2.el10_3.2` from Rocky CRB, key `6fedfc85`
- `zabbix-selinux-policy-2:8.0.0-release1.el10` from official Zabbix, key `b5333005`

It temporarily masks only the SELinux fact seen by the upstream role and restores
the complete original fact in `always`; kernel enforcing mode is checked before
and after. Remove this adapter when the pinned upstream defect is fixed.

Custom built-in `uri` calls are required because the controller cannot reach the
management-only frontend and upstream agent API tasks use a different transport.
Every secret-bearing request delegates over SSH to the configured Zabbix server,
calls loopback with `use_proxy: false`, and uses `no_log`/`diff: false`. Zabbix 8
bearer authentication, exact object resolution, ownership tagging, unowned-host
refusal, explicit update fields, and exact readback are local security policy.

`requirements.yml` pins the complete dependency closure used by
`community.zabbix` 4.3.0. Checksums are verified by
`scripts/verify_collection_artifacts.py`; the remaining known hashes are encoded
there and downloaded only to caller-provided scratch storage.
