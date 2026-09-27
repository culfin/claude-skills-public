#!/usr/bin/env bash
# updates.sh — weekly report of pending package updates per server.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_info "updates: ${SERVER_NAME}"

remote_exec "$SERVER_NAME" "apt-get update -qq" 120 > /dev/null || {
    log_error "apt-get update failed on ${SERVER_NAME}"
    exit 1
}

UPGRADABLE=$(remote_exec "$SERVER_NAME" "apt list --upgradable 2>/dev/null | grep -c upgradable || true" 30)
SECURITY=$(remote_exec "$SERVER_NAME" "apt list --upgradable 2>/dev/null | grep -c -- -security || true" 30)
UA_TIMER=$(remote_exec "$SERVER_NAME" "systemctl is-active apt-daily-upgrade.timer || true" 15)
REBOOT=$(remote_exec "$SERVER_NAME" "test -f /var/run/reboot-required && echo yes || echo no" 15)

UPGRADABLE=${UPGRADABLE//[^0-9]/}
SECURITY=${SECURITY//[^0-9]/}

push_metric updates_available "${UPGRADABLE:-0}"
push_metric updates_security "${SECURITY:-0}"
push_metric reboot_required "$([[ "$REBOOT" == yes ]] && echo 1 || echo 0)"

if [[ "${SECURITY:-0}" -gt 0 ]]; then
    send_alert warning "Security updates: ${SERVER_NAME}" "${SECURITY} security updates pending"
fi
if [[ "$UA_TIMER" != "active" ]]; then
    send_alert warning "Unattended upgrades off: ${SERVER_NAME}" "apt-daily-upgrade.timer is ${UA_TIMER}"
fi

echo "SUMMARY: Updates: ${UPGRADABLE:-0} (${SECURITY:-0} security) | Unattended: ${UA_STATUS} | Reboot: ${REBOOT}"
