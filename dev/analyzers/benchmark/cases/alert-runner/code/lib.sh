#!/usr/bin/env bash
# lib.sh — shared helpers for the monitoring scripts.

STATE_DIR="${STATE_DIR:-/var/lib/monitor}"
mkdir -p "$STATE_DIR/dedup"

log_info()  { echo "[INFO]  $(date '+%F %T') $*"; }
log_error() { echo "[ERROR] $(date '+%F %T') $*" >&2; }

# Run a command on a host from hosts.conf. Prints its output; returns ssh's exit code.
remote_exec() {
    local host="$1" cmd="$2" timeout="${3:-30}" line ip user key
    line=$(grep -E "^${host}\|" /config/hosts.conf | head -1) || return 1
    IFS='|' read -r _ ip user key <<< "$line"
    local encoded
    encoded=$(printf '%s' "$cmd" | base64 | tr -d '\n')
    timeout "$(( timeout + 10 ))" ssh -n -i "$key" -o BatchMode=yes -o ConnectTimeout=10 \
        "${user}@${ip}" "echo ${encoded} | base64 -d | bash" 2>&1
}

# True if no alert with this id was sent within the last N hours; records the send time.
dedup_ok() {
    local id="$1" hours="$2" f="$STATE_DIR/dedup/$1"
    if [[ -f "$f" ]]; then
        local age=$(( $(date +%s) - $(cat "$f") ))
        (( age < hours * 3600 )) && return 1
    fi
    date +%s > "$f"
    return 0
}

send_push() {
    local level="$1" title="$2" message="$3"
    curl -s --max-time 10 \
        --form-string "token=${PUSH_TOKEN}" \
        --form-string "user=${PUSH_USER}" \
        --form-string "title=${title}" \
        --form-string "message=${message}" \
        --form-string "priority=$([[ "$level" == critical ]] && echo 1 || echo 0)" \
        https://api.pushover.net/1/messages.json > /dev/null || log_error "push failed: ${title}"
}
