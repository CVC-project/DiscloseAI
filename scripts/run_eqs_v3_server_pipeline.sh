#!/usr/bin/env bash
# Run remaining listed-company collection batches sequentially on the server.
set -euo pipefail

ROOT="${ROOT:-/data/discloseai/workspace/DiscloseAI-eqs-v3}"
DATA_DIR="${DATA_DIR:-/data/discloseai}"
OUTPUT="$DATA_DIR/financial/eqs_v3_panels_2021_2025.json"
LISTED_TICKERS="$DATA_DIR/profiles/krx_listed_tickers.json"
EXCLUSION_FILE="$DATA_DIR/eqs/eqs_v3_excluded_unverifiable.json"
LOG_DIR="$DATA_DIR/manifests"
PYTHON="$ROOT/.venv/bin/python"

wait_for_pid_file() {
    local pid_file="$1"
    [[ -f "$pid_file" ]] || return 0
    local batch_pid
    batch_pid="$(tr -d '[:space:]' < "$pid_file")"
    [[ -n "$batch_pid" ]] || return 0
    while kill -0 "$batch_pid" 2>/dev/null; do
        sleep 30
    done
}

run_batch() {
    local label="$1"
    local limit="$2"
    local log="$LOG_DIR/eqs_v3_${label}.log"
    echo "[$(date -Is)] starting $label" | tee -a "$LOG_DIR/eqs_v3_pipeline.log"
    local exclude_args=()
    if [[ -f "$EXCLUSION_FILE" ]]; then
        exclude_args=(--exclude-file "$EXCLUSION_FILE")
    fi
    DISCLOSEAI_FINANCIAL_DATA_DIR="$DATA_DIR/profiles" \
        "$PYTHON" "$ROOT/scripts/collect_eqs_v3_panels.py" \
        --years 5 --limit "$limit" --sleep 0.45 \
        --listed-tickers-file "$LISTED_TICKERS" --output "$OUTPUT" \
        "${exclude_args[@]}" \
        > "$log" 2>&1
    echo "[$(date -Is)] finished $label" | tee -a "$LOG_DIR/eqs_v3_pipeline.log"
}

mkdir -p "$LOG_DIR"
cd "$ROOT"

# Batch 3 is already running. Wait for it before starting fresh targets.
wait_for_pid_file "$LOG_DIR/eqs_v3_batch_03.pid"
run_batch "batch_04" 600
run_batch "batch_05" 600

# With --retry-empty omitted, only never-completed requests remain. Companies
# with valid but short history, or no DART annual panel, stay marked attempted.
run_batch "recovery_01" 0
run_batch "recovery_02" 0

touch "$LOG_DIR/eqs_v3_pipeline_complete"
echo "[$(date -Is)] pipeline complete" | tee -a "$LOG_DIR/eqs_v3_pipeline.log"
