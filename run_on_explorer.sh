#!/usr/bin/env bash
set -euo pipefail

# Make conda available and activate env INSIDE the job shell
source /shared/EL9/explorer/anaconda3/2024.06/etc/profile.d/conda.sh
conda activate pranpyrk

# Ensure PyRK is importable
export PYTHONPATH="/home/wuppuluru.p/pyrk:${PYTHONPATH:-}"

MANIFEST="/home/wuppuluru.p/pyrk/pbfhr_manifest.txt"
OUTCSV_NAME="power.csv"
OUTLOG_DIR="/home/wuppuluru.p/pyrk/pbfhr_logs"
mkdir -p "$OUTLOG_DIR"

echo "python=$(which python)"
python -c "import sys; print('exe=', sys.executable)"
python -c "import pyrk; print('pyrk=', pyrk.__file__)"

N=$(wc -l < "$MANIFEST")
proc=${SLURM_PROCID:-0}
ntasks=${SLURM_NTASKS:-1}

echo "$N scenarios in total"
echo "This is proc $proc of $ntasks"

for ((i=proc; i<N; i+=ntasks)); do
	run_dir=$(sed -n "$((i+1))p" "$MANIFEST")
	run_name=$(basename "$run_dir")

	echo "Starting $run_name"

	(
	cd "$run_dir"
	python -m pyrk.driver \
		--infile=input.py \
		--plotdir=. \
		--outcsv="$OUTCSV_NAME"
	) > "$OUTLOG_DIR/${run_name}.log" 2>&1
	echo "Done $run_name"
done

