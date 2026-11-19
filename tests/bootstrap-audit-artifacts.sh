#!/usr/bin/env bash
set -euo pipefail

artifact_dir="${ZABBIX_AUDIT_DIR:-tests/artifacts}"
mkdir -p "$artifact_dir"

ansible-galaxy collection download community.zabbix:4.3.0 \
  --no-deps -p "$artifact_dir"
printf '%s  %s\n' \
  d30bbf022bc32bae89771f8d3611b31d9a524f5d384ff600067e7d0ba9480a5a \
  "$artifact_dir/community-zabbix-4.3.0.tar.gz" | sha256sum --check --strict
