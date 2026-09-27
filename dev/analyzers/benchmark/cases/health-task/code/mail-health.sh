#!/usr/bin/env bash
# mail-health.sh — daily check of a mail server: queue size, oldest mail, service state.
# Called by the scheduler with SERVER_NAME set; pushes metrics and sends alerts.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

log_info "mail-health: ${SERVER_NAME}"

REMOTE='
echo "===QUEUE==="
postqueue -p 2>/dev/null | tail -1
echo "===OLDEST==="
postqueue -j 2>/dev/null | grep -oE "\"arrival_time\":[ ]*[0-9]+" | grep -oE "[0-9]+" | sort -n | head -1
echo "===POSTFIX==="
systemctl is-active postfix
echo "===DOVECOT==="
systemctl is-active dovecot
echo "===END==="
'

OUTPUT=$(remote_exec "$SERVER_NAME" "$REMOTE" 60)

section() { printf '%s\n' "$OUTPUT" | awk -v s="===$1===" '$0==s{on=1;next} /^===/{on=0} on' | head -5; }

QUEUE_LINE=$(section QUEUE)
OLDEST_EPOCH=$(section OLDEST | grep -oE '^[0-9]+' | head -1)
POSTFIX_STATE=$(section POSTFIX | tr -d '[:space:]')
DOVECOT_STATE=$(section DOVECOT | tr -d '[:space:]')

QUEUE_SIZE=0
if ! printf '%s' "$QUEUE_LINE" | grep -qi "queue is empty"; then
    QUEUE_SIZE=$(printf '%s' "$QUEUE_LINE" | grep -oE '[0-9]+ Request' | grep -oE '[0-9]+' || echo 0)
fi

OLDEST_MIN=0
if [[ -n "$OLDEST_EPOCH" ]]; then
    OLDEST_MIN=$(( ( $(date +%s) - OLDEST_EPOCH ) / 60 ))
fi

push_metric mail_queue_size "$QUEUE_SIZE"
push_metric mail_queue_oldest_min "$OLDEST_MIN"
push_metric mail_postfix_active "$([[ "$POSTFIX_STATE" == active ]] && echo 1 || echo 0)"
push_metric mail_dovecot_active "$([[ "$DOVECOT_STATE" == active ]] && echo 1 || echo 0)"

if [[ "$QUEUE_SIZE" -gt 50 ]]; then
    send_alert warning "Mail queue backing up: ${SERVER_NAME}" "${QUEUE_SIZE} mails in queue"
elif [[ "$OLDEST_MIN" -gt 240 ]]; then
    send_alert warning "Mail stuck in queue: ${SERVER_NAME}" "oldest mail waiting $(( OLDEST_MIN / 60 ))h"
fi

if [[ "$POSTFIX_STATE" != "active" ]]; then
    send_alert critical "Postfix DOWN: ${SERVER_NAME}" "postfix.service is not active"
fi
if [[ "$DOVECOT_STATE" != "active" ]]; then
    send_alert critical "Dovecot DOWN: ${SERVER_NAME}" "dovecot.service is not active"
fi

echo "SUMMARY: queue=${QUEUE_SIZE}, oldest=${OLDEST_MIN}min, postfix=${POSTFIX_STATE}, dovecot=${DOVECOT_STATE}"
