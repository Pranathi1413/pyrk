#!/usr/bin/env python3

from dataclasses import dataclass
from string import Template
from pathlib import Path

TEMPLATE_PATH = "examples/pbfhr/input_template.py"
OUTPUT_ROOT = "pbfhr_runs"
MANIFEST_PATH = "pbfhr_manifest.txt"

# Mk1 PB-FHR rated thermal power (W)
P_NOM_TH = 236e6

POWER_LEVELS = [0.2, 0.3, 0.5, 0.7, 0.8]

# Temperature buckets
TEMP_BUCKETS = ["low", "nominal", "high"]

# Ramping details (same for all scenarios)
PRE_RAMP_S   = 2.0    # seconds of steady-state before ramp
RAMP_TIME_S  = 300.0   # duration of reactivity ramp
POST_RAMP_S  = 5.0   # seconds after ramp with constant reactivity

# Reactivity ramp rate (pcm per minute) - tuned to get ~1%/min power ramp
RHO_RATE_PCM_PER_MIN = 240.0


@dataclass
class Scenario:
    p0: float          # initial power
    direction: str     # "up" or "down"
    bucket: str        # "low", "nominal", "high"
    t_ramp_s: float    # ramp duration (RAMP_TIME_S)
    run_name: str      # folder name


def generate_scenarios():
    """
    For each (initial power, bucket), create:
      - one 'up' ramp scenario
      - one 'down' ramp scenario
    """
    scenarios = []
    for bucket in TEMP_BUCKETS:
        for p0 in POWER_LEVELS:
            # Ramp up scenario
            run_name_up = f"init{int(p0*100)}-{bucket}-up"
            scenarios.append(
                Scenario(
                    p0=p0,
                    direction="up",
                    bucket=bucket,
                    t_ramp_s=RAMP_TIME_S,
                    run_name=run_name_up,
                )
            )

            # Ramp down scenario
            run_name_dn = f"init{int(p0*100)}-{bucket}-down"
            scenarios.append(
                Scenario(
                    p0=p0,
                    direction="down",
                    bucket=bucket,
                    t_ramp_s=RAMP_TIME_S,
                    run_name=run_name_dn,
                )
            )
    return scenarios


def initial_temps_kelvin(bucket: str):
    if bucket == "low":
        # slightly cooler than nominal
        t_cool_C  = 620.0
        t_fuel_C  = 750.0
        t_mod_C   = 740.0
        t_shell_C = 730.0

    elif bucket == "high":
        # slightly hotter than nominal
        t_cool_C  = 680.0
        t_fuel_C  = 850.0
        t_mod_C   = 840.0
        t_shell_C = 820.0

    else:  # "nominal" -- match the original example
        t_cool_C  = 650.0
        t_fuel_C  = 800.0
        t_mod_C   = 800.0
        t_shell_C = 770.0

    K = 273.15
    return (
        t_fuel_C + K,
        t_mod_C + K,
        t_shell_C + K,
        t_cool_C + K,
    )


def build_input_from_template(template_text: str, scen: Scenario) -> str:
    """
    Substitute scenario-specific values into the template.

    Template placeholders:
      $TF
      $T_RAMP_START
      $T_RAMP_END
      $DELTA_RHO
      $POWER_TOT
      $T_FUEL0
      $T_MOD0
      $T_SHELL0
      $T_COOL0
    """

    # Total simulation time = pre + ramp + post
    tf = PRE_RAMP_S + scen.t_ramp_s + POST_RAMP_S

    t_ramp_start = PRE_RAMP_S
    t_ramp_end   = PRE_RAMP_S + scen.t_ramp_s

    # rho_rate [pcm/min] * (t_ramp_s [s] / 60) => pcm
    delta_rho_pcm = RHO_RATE_PCM_PER_MIN * (scen.t_ramp_s / 60.0)

    # Sign based on direction
    if scen.direction == "down":
        delta_rho_pcm = -delta_rho_pcm

    # Use nominal PB-FHR power for TH scaling
    power_tot = scen.p0 * P_NOM_TH

    # Initial temperatures for bucket
    t_fuel0, t_mod0, t_shell0, t_cool0 = initial_temps_kelvin(scen.bucket)

    tmpl = Template(template_text)
    filled = tmpl.substitute(
        TF=f"{tf:.6f}",
        T_RAMP_START=f"{t_ramp_start:.6f}",
        T_RAMP_END=f"{t_ramp_end:.6f}",
        DELTA_RHO=f"{delta_rho_pcm:.6f}",
        POWER_TOT=f"{power_tot:.6e}",
        T_FUEL0=f"{t_fuel0:.6f} * units.kelvin",
        T_MOD0=f"{t_mod0:.6f} * units.kelvin",
        T_SHELL0=f"{t_shell0:.6f} * units.kelvin",
        T_COOL0=f"{t_cool0:.6f} * units.kelvin",
    )
    return filled


def write_input_file(run_dir: Path, input_text: str) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    input_path = run_dir / "input.py"
    with input_path.open("w", encoding="utf-8") as f:
        f.write(input_text)
    return input_path


def main():
    template_path = Path(TEMPLATE_PATH)
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    template_text = template_path.read_text(encoding="utf-8")

    output_root = Path(OUTPUT_ROOT)
    output_root.mkdir(exist_ok=True)

    scenarios = generate_scenarios()
    print(f"Generated {len(scenarios)} scenarios.")

    manifest_lines = []

    for scen in scenarios:
        run_dir = output_root / scen.run_name
        input_text = build_input_from_template(template_text, scen)
        write_input_file(run_dir, input_text)
        manifest_lines.append(str(run_dir))

    # Write manifest file with one run directory per line
    manifest_path = Path(MANIFEST_PATH)
    manifest_path.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")

    print(f"Wrote manifest to {manifest_path} with {len(manifest_lines)} entries.")


if __name__ == "__main__":
    main()
