# Changelog

## Unreleased

- Publish the role as `tuxbull.zabbix_agent` from repository
  `ansible.zabbix_agent`, while retaining the `zabbix_onboarding_*` variable API.
- Derive the role from template revision
  `479eda20a4317ca930de3b04b7d6c0fd87008951` while preserving dispatcher files.
- Wrap pinned `community.zabbix` 4.3.0 for Rocky 10 Agent2 installation and PSK configuration.
- Add exact-source firewalld policy and delegated Zabbix 8 API registration with ownership safeguards.
- Validate the signed Agent2 package with its full epoch-bearing EVR.
- Preserve all prior template changelog history below.

## [1.5.1] - 2026-11-04

### Changed

- Align Galaxy metadata, smoke tests, documentation, and maintainer guidance
  with the `tuxbull` namespace and Tuxbull-Open-Source workflow.
- Add the repository-versioned `skills/ansible-role-template/SKILL.md`.
- Establish `tasks/main.yml` and `tasks/include-file.yml` as the protected
  dispatcher core: update them only through a reviewed template PR, then align
  derived roles from the merged template.

## [1.5.0] - 2026-10-27

- Expanded supported controller role discovery and updated documentation.

## [1.4] - 2025-01-26

- Removed legacy Python handling for EL 6–8.

## [1.3] - 2024-09-17

- Added dynamic task directory variables.

## [1.2] - 2023-05-17

- Fixed Rocky Linux 9 `ansible.cfg` handling.

## [1.1] - 2022-10-18

- Added RHEL-clone distribution grouping.

## [1.0] - 2022-03-20

- First published release.
