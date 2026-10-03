#!/usr/bin/env bash
# load-ok.sh — may another parallel implementer start? Exit 0 if the 1-minute load average is
# below the number of cores, else 1. Prints "load <x> cores <n>".
# Why: parallel builds and test runs on an already busy machine make everything slower — one
# overloaded host once reached load 102 and turned unrelated checks into timeouts.
# DEV_LOAD / DEV_CORES override the measurement (tests).
set -uo pipefail
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
