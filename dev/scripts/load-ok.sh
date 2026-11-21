#!/usr/bin/env bash
# load-ok.sh — may another parallel implementer start? Exit 0 if the 1-minute load average is
# below the number of cores, else 1. Prints "load <x> cores <n>".
# Why: parallel builds and test runs on an already busy machine make everything slower — one
# overloaded host once reached load 102 and turned unrelated checks into timeouts.
# `--wait`: poll every 60 s until the load is below the cores (exit 0) or 10 minutes have passed
# (exit 1) — ONE background command instead of one wake-up per check.
# DEV_LOAD / DEV_CORES override the measurement, DEV_WAIT_STEP / DEV_WAIT_MAX (seconds) the polling (tests).
set -uo pipefail
if [[ "${1:-}" == "--wait" ]]; then
    step="${DEV_WAIT_STEP:-60}"; max="${DEV_WAIT_MAX:-600}"; waited=0
    while ! bash "$0"; do
        (( waited >= max )) && exit 1
        sleep "$step"; waited=$((waited + step))
    done
    exit 0
fi
load="${DEV_LOAD:-}"; cores="${DEV_CORES:-}"
if [[ -z "$load" ]]; then
    if [[ -r /proc/loadavg ]]; then load=$(cut -d' ' -f1 /proc/loadavg)
    else load=$(sysctl -n vm.loadavg 2>/dev/null | tr -d '{}' | awk '{print $1}' | tr ',' '.'); fi
fi
if [[ -z "$cores" ]]; then
    cores=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 1)
fi
echo "load ${load:-unknown} cores $cores"
[[ -n "$load" ]] || exit 1          # unknown load = do not add more work
awk -v l="$load" -v c="$cores" 'BEGIN { exit !(l < c) }'
