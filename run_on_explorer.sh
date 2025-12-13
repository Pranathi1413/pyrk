#!/usr/bin/env bash
set -euo pipefail

MANIFEST="pbfhr_manifest.txt"
PYRK_DRIVER="pyrk/driver.py"
OUTCSV_NAME="power.csv"

THREADS="${SLURM_CPUS_PER_TASK:-1}"
OUTLOG_DIR="pbfhr_logs"
mkdir -p "$OUTLOG_DIR"

N=$(wc -l < "$MANIFEST")
proc=${SLURM_PROCID:-0}
ntasks=${SLURM_NTASKS:-1}

echo "$N scenarios in total"
echo "This is proc $proc of $ntasks"

for ((i=proc; i<N; i+=ntasks)); do
  run_dir=$(sed -n "$((i+1))p" "$MANIFEST")
  run_name=$(basename "$run_dir")

  echo "Starting scenario $run_name in $run_dir"

  (
    cd "$run_dir"
    mkdir -p output
    python "$PYRK_DRIVER" \
      --infile=input.py \
      --plotdir=output \
      --outcsv="$OUTCSV_NAME"
  ) > "$OUTLOG_DIR/${run_name}.log" 2>&1

  echo "Done scenario $run_name"
done
