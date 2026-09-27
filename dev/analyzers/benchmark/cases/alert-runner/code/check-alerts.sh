#!/usr/bin/env bash
# check-alerts.sh — runs every 5 minutes from cron inside the monitoring container.
# Queries Prometheus for a list of conditions and sends a push message per new problem.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

PROM="http://prometheus:9090"
DEDUP_HOURS=4

should_alert() { dedup_ok "prom-${1}" "$DEDUP_HOURS"; }

# Instances matching a PromQL condition, one per line.
prom_instances() {
    local query="$1" result
    result=$(curl -sf --max-time 10 \
        "${PROM}/api/v1/query?query=$(printf '%s' "$query" | sed 's/ /%20/g; s/"/%22/g')" \
        2>/dev/null || echo '{"status":"error"}')
    printf '%s' "$result" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
    for r in data.get("data", {}).get("result", []):
        print(r["metric"].get("instance", "unknown"))
except Exception:
    pass
'
}

log_info "alert run start"

# 1: host down
while read -r instance; do
    [[ -z "$instance" ]] && continue
    if should_alert "down-${instance}"; then
        send_push "critical" "Host DOWN: ${instance}" "node_exporter unreachable for 2+ minutes"
    fi
done <<< "$(prom_instances 'up{job="node"} == 0')"

# 2: website down (only when the prober itself is up)
while read -r instance; do
    [[ -z "$instance" ]] && continue
    if should_alert "web-${instance}"; then
        send_push "critical" "Website DOWN: ${instance}" "probe failed"
    fi
done <<< "$(prom_instances 'probe_success{job="blackbox"} == 0')"

# 3: disk above 90 %
while read -r instance; do
    [[ -z "$instance" ]] && continue
    if should_alert "disk-${instance}"; then
        send_push "warning" "Disk almost full: ${instance}" "more than 90 % used"
    fi
done <<< "$(prom_instances '(1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) > 0.9')"

# 4: CI worker hanging — a job process older than 3 hours on the build host
WORKER_PROCS=$(remote_exec build-host "ps -eo etimes=,args=" 20)
HUNG_AGE=$(printf '%s\n' "$WORKER_PROCS" | grep -m1 'Runner\.Worker' | awk '{print $1}')
if [[ -n "$HUNG_AGE" && "$HUNG_AGE" -gt 10800 ]]; then
    if should_alert "ci-hung"; then
        send_push "warning" "CI job hanging" "Runner.Worker running for $(( HUNG_AGE / 3600 ))h"
    fi
fi

# 5: certificates expiring within 14 days
while read -r instance; do
    [[ -z "$instance" ]] && continue
    if should_alert "cert-${instance}"; then
        send_push "warning" "Certificate expiring: ${instance}" "less than 14 days left"
    fi
done <<< "$(prom_instances '(probe_ssl_earliest_cert_expiry - time()) / 86400 < 14')"

# 6: backup older than 26 hours
while read -r instance; do
    [[ -z "$instance" ]] && continue
    if should_alert "backup-${instance}"; then
        send_push "critical" "Backup stale: ${instance}" "last successful backup older than 26 h"
    fi
done <<< "$(prom_instances '(time() - backup_last_success_timestamp) > 93600')"

log_info "alert run done"
