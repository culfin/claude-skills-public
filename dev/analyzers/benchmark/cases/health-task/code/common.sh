#!/usr/bin/env bash
# common.sh — shared helpers for maintenance tasks.

log_info()  { echo "[INFO]  $(date '+%F %T') $*"; }
log_error() { echo "[ERROR] $(date '+%F %T') $*" >&2; }

# Run a command on a server from servers.conf; prints output, returns ssh's exit code.
remote_exec() {
    local name="$1" cmd="$2" timeout="${3:-30}" line ip user key
    line=$(grep -E "^${name}\|" /config/servers.conf | head -1) || return 1
    IFS='|' read -r _ ip user key <<< "$line"
    local encoded
    encoded=$(printf '%s' "$cmd" | base64 | tr -d '\n')
    timeout "$(( timeout + 10 ))" ssh -n -i "$key" -o BatchMode=yes -o ConnectTimeout=10 \
        "${user}@${ip}" "echo ${encoded} | base64 -d | bash" 2>/dev/null
}

push_metric() {
    local name="$1" value="$2"
    printf '%s{instance="%s"} %s\n' "$name" "$SERVER_NAME" "$value" \
        | curl -s --max-time 5 --data-binary @- "http://pushgateway:9091/metrics/job/maintenance/instance/${SERVER_NAME}" > /dev/null || true
}

send_alert() {
    local level="$1" title="$2" message="$3"
    log_info "ALERT [${level}] ${title}: ${message}"
    curl -s --max-time 10 --form-string "title=${title}" --form-string "message=${message}" \
        "${ALERT_URL:-http://alerts:8080/send}" > /dev/null || log_error "alert failed: ${title}"
}
