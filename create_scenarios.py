#!/usr/bin/env python3

from dataclasses import dataclass
from string import Template
from pathlib import Path

# Paths
TEMPLATE_PATH = "examples/pbfhr/input_template.py"
OUTPUT_ROOT = "pbfhr_runs"
MANIFEST_PATH = "pbfhr_manifest.txt"

# PB-FHR rated thermal power (W)
P_NOM_TH = 236e6

# Power ladder (fractions of rated)
POWER_LEVELS = [0.2, 0.5, 1.0]

# Temperature buckets
TEMP_BUCKETS = ["low", "nominal", "high"]

# Timing (kept reasonable)
PRE_RAMP_S  = 80.0
POST_RAMP_S = 80.0

# Desired power ramp rate (fraction of rated per minute)
POWER_RAMP_RATE_PER_MIN = 0.05   # 5% / min

# Reactivity ramp rate (pcm / min) — calibrated manually
RHO_RATE_PCM_PER_MIN = 240.0

# Initial external reactivity bias (pcm)
# Non-zero to avoid initial power decay
RHO_BIAS_PCM = 200.0


@dataclass
class Scenario:
    p0: float
    p1: float
    direction: str   # "up" or "down"
    bucket: str
    t_ramp_s: float
    run_name: str


def initial_temps_kelvin(bucket: str):
    if bucket == "low":
        t_cool_C  = 620.0
        t_fuel_C  = 750.0
        t_mod_C   = 740.0
        t_shell_C = 730.0
    elif bucket == "high":
        t_cool_C  = 680.0
        t_fuel_C  = 850.0
        t_mod_C   = 840.0
        t_shell_C = 820.0
    else:  # nominal
        t_cool_C  = 650.0
        t_fuel_C  = 800.0
        t_mod_C   = 800.0
        t_shell_C = 770.0

    K = 273.15
    return (t_fuel_C + K, t_mod_C + K, t_shell_C + K, t_cool_C + K)


def ramp_time_seconds(p0: float, p1: float) -> float:
    delta_p = abs(p1 - p0)
    minutes = delta_p / POWER_RAMP_RATE_PER_MIN
    return minutes * 60.0


def generate_scenarios():
    scenarios = []

    for bucket in TEMP_BUCKETS:
        for i in range(len(POWER_LEVELS)):
            p_lo = POWER_LEVELS[i]
            p_hi = POWER_LEVELS[i] + 0.1

            # Ramp UP
            if (p_lo < 1):
                t_ramp = ramp_time_seconds(p_lo, p_hi)
                scenarios.append(
                    Scenario(
                        p0=p_lo,
                        p1=p_hi,
                        direction="up",
                        bucket=bucket,
                        t_ramp_s=t_ramp,
                        run_name=f"{int(p_lo*100)}-{int(p_hi*100)}-{bucket}-up",
                    )
                )

            p_lo = POWER_LEVELS[i] - 0.1
            p_hi = POWER_LEVELS[i]

            # Ramp DOWN
            if (p_lo > 0.2):
                t_ramp = ramp_time_seconds(p_hi, p_lo)
                scenarios.append(
                    Scenario(
                        p0=p_hi,
                        p1=p_lo,
                        direction="down",
                        bucket=bucket,
                        t_ramp_s=t_ramp,
                        run_name=f"{int(p_hi*100)}-{int(p_lo*100)}-{bucket}-down",
                    )
                )

    return scenarios


def build_input_from_template(template_text: str, scen: Scenario) -> str:
    tf = PRE_RAMP_S + scen.t_ramp_s + POST_RAMP_S
    t_ramp_start = PRE_RAMP_S
    t_ramp_end = PRE_RAMP_S + scen.t_ramp_s

    # Reactivity ramp magnitude
    delta_rho_pcm = RHO_RATE_PCM_PER_MIN * (scen.t_ramp_s / 60.0)
    rho_bias_pcm = RHO_BIAS_PCM
    if scen.direction == "down":
        delta_rho_pcm = -delta_rho_pcm
        rho_bias_pcm = 0

    # Thermal power scaling matches initial power level
    power_tot = scen.p0 * P_NOM_TH

    t_fuel0, t_mod0, t_shell0, t_cool0 = initial_temps_kelvin(scen.bucket)

    tmpl = Template(template_text)
    return tmpl.substitute(
        TF=f"{tf:.6f}",
        T_RAMP_START=f"{t_ramp_start:.6f}",
        T_RAMP_END=f"{t_ramp_end:.6f}",
        RHO_BIAS_PCM=f"{rho_bias_pcm:.6f}",
        DELTA_RHO_PCM=f"{delta_rho_pcm:.6f}",
        POWER_TOT=f"{power_tot:.6e}",
        T_FUEL0=f"{t_fuel0:.6f} * units.kelvin",
        T_MOD0=f"{t_mod0:.6f} * units.kelvin",
        T_SHELL0=f"{t_shell0:.6f} * units.kelvin",
        T_COOL0=f"{t_cool0:.6f} * units.kelvin",
    )


def write_input_file(run_dir: Path, input_text: str):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "input.py").write_text(input_text, encoding="utf-8")


def main():
    template_text = Path(TEMPLATE_PATH).read_text(encoding="utf-8")

    output_root = Path(OUTPUT_ROOT)
    output_root.mkdir(exist_ok=True)

    scenarios = generate_scenarios()
    print(f"Generated {len(scenarios)} scenarios.")

    manifest = []
    for scen in scenarios:
        run_dir = output_root / scen.run_name
        input_text = build_input_from_template(template_text, scen)
        write_input_file(run_dir, input_text)
        manifest.append(str(run_dir))

    Path(MANIFEST_PATH).write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print(f"Wrote manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
