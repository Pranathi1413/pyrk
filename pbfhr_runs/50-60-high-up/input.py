"""
PB-FHR PyRK input TEMPLATE (scenario-filled via string.Template)

Placeholders filled by create_scenarios.py:

  280.000000
  80.000000
  200.000000
  200.000000
  480.000000
  1.180000e+08
  1123.150000 * units.kelvin
  1113.150000 * units.kelvin
  1093.150000 * units.kelvin
  953.150000 * units.kelvin
"""

from pyrk.utilities.ur import units
from pyrk import th_component as th
import math
from pyrk.materials.material import Material
from pyrk.materials.liquid_material import LiquidMaterial
from pyrk.density_model import DensityModel
from pyrk.convective_model import ConvectiveModel
import random
from pyrk.timer import Timer
import numpy as np

#############################################
# Simulation parameters
#############################################

t0 = 0.0 * units.seconds
dt = 0.02 * units.seconds
tf = 280.000000 * units.seconds

# Temperature feedbacks of reactivity
alpha_fuel = random.gauss(-3.19, 0.1595) * units.pcm / units.kelvin
alpha_mod = -0.7 * units.pcm / units.kelvin
alpha_shell = 0 * units.pcm / units.kelvin
alpha_cool = random.gauss(0.23, 0.11) * units.pcm / units.kelvin

# Initial temperatures (already in kelvin)
t_mod   = 1113.150000 * units.kelvin
t_fuel  = 1123.150000 * units.kelvin
t_shell = 1093.150000 * units.kelvin
t_cool  = 953.150000 * units.kelvin

# Total thermal power (used by TH heat generation scaling)
power_tot = 1.180000e+08 * units.watt

kappa = 0.0

#############################################
# Geometry helpers
#############################################

def area_sphere(r):
    assert r >= 0 * units.meter
    return 4.0 * math.pi * pow(r.to("meter"), 2)

def vol_sphere(r):
    assert r >= 0 * units.meter
    return (4.0 / 3.0) * math.pi * pow(r.to("meter"), 3)

#############################################
# Pebble volumes (same as example)
#############################################

n_pebbles = 470000
r_mod   = 1.25 / 100.0 * units.meter
r_fuel  = 1.4  / 100.0 * units.meter
r_shell = 1.5  / 100.0 * units.meter

vol_mod   = vol_sphere(r_mod)
vol_fuel  = vol_sphere(r_fuel)  - vol_sphere(r_mod)
vol_shell = vol_sphere(r_shell) - vol_sphere(r_fuel)
vol_cool  = (vol_mod + vol_fuel + vol_shell) * 0.4 / 0.6
a_pb = area_sphere(r_shell)

#############################################
# Required input
#############################################

ti = Timer(t0=t0, tf=tf, dt=dt)

n_pg = 6
n_dg = 0

fission_iso = "u235"
spectrum = "thermal"

n_ref = 0
Lambda_ref = 0
ref_lambda = []
ref_rho = []

feedback = True

# External reactivity: start at bias, ramp by delta, hold final
from pyrk.reactivity_insertion import RampReactivityInsertion
rho_bias = 200.000000 * units.pcm
delta_rho = 480.000000 * units.pcm

rho_ext = RampReactivityInsertion(
    timer=ti,
    t_start=80.000000 * units.seconds,
    t_end=200.000000 * units.seconds,
    rho_init=rho_bias,
    rho_rise=(rho_bias + delta_rho),
    rho_final=(rho_bias + delta_rho),
)

nsteps = 5000

#############################################
# Materials (same distributions as example)
#############################################

k_mod = random.gauss(17, 17 * 0.05) * units.watt / (units.meter * units.kelvin)
cp_mod = random.gauss(1650.0, 1650.0 * 0.05) * units.joule / (units.kg * units.kelvin)
rho_mod = DensityModel(a=1740.0 * units.kg / (units.meter**3), model="constant")
Moderator = Material("mod", k_mod, cp_mod, dm=rho_mod)

k_fuel = random.uniform(15.0, 19.0) * units.watt / (units.meter * units.kelvin)
cp_fuel = random.gauss(1818.0, 1818.0 * 0.05) * units.joule / (units.kg * units.kelvin)
rho_fuel = DensityModel(a=2220.0 * units.kg / (units.meter**3), model="constant")
Fuel = Material("fuel", k_fuel, cp_fuel, dm=rho_fuel)

k_shell = random.gauss(17, 17 * 0.05) * units.watt / (units.meter * units.kelvin)
cp_shell = random.gauss(1650.0, 1650.0 * 0.05) * units.joule / (units.kg * units.kelvin)
rho_shell = DensityModel(a=1740.0 * units.kg / (units.meter**3), model="constant")
Shell = Material("shell", k_shell, cp_shell, dm=rho_shell)

k_cool = 1.0 * units.watt / (units.meter * units.kelvin)
cp_cool = random.gauss(2415.78, 2415.78 * 0.05) * units.joule / (units.kg * units.kelvin)
rho_cool = DensityModel(
    a=2415.6 * units.kg / (units.meter**3),
    b=0.49072 * units.kg / (units.meter**3) / units.kelvin,
    model="linear",
)
mu0 = 0 * units.pascal * units.second
cool_mat = LiquidMaterial("cool", k_cool, cp_cool, rho_cool, mu0)

# Coolant flow properties
h_cool_rd = random.gauss(4700.0, 4700.0 * 0.05) * units.watt / units.kelvin / units.meter**2
h_cool = ConvectiveModel(h0=h_cool_rd, mat=cool_mat, model="constant")
m_flow = 976.0 * units.kg / units.second
t_inlet = units.Quantity(600.0, units.degC)

#############################################
# TH components (same as example)
#############################################

mod = th.THComponent(
    name="mod", mat=Moderator, vol=vol_mod, T0=t_mod, alpha_temp=alpha_mod,
    timer=ti, sph=True, ri=0.0 * units.meter, ro=r_mod,
)

fuel = th.THComponent(
    name="fuel", mat=Fuel, vol=vol_fuel, T0=t_fuel, alpha_temp=alpha_fuel,
    timer=ti, heatgen=True, power_tot=power_tot / n_pebbles,
    sph=True, ri=r_mod, ro=r_fuel,
)

shell = th.THComponent(
    name="shell", mat=Shell, vol=vol_shell, T0=t_shell, alpha_temp=alpha_shell,
    timer=ti, sph=True, ri=r_fuel, ro=r_shell,
)

# Mesh size: keep moderate for runtime
l = 0.001 * units.meter
comp_list = mod.mesh(l)
comp_list.extend(fuel.mesh(l))
comp_list.extend(shell.mesh(l))
pebble = th.THSuperComponent("pebble", t_shell, comp_list, timer=ti)
pebble.add_conv_bc("cool", h=h_cool)

cool = th.THComponent(
    name="cool", mat=cool_mat, vol=vol_cool, T0=t_cool, alpha_temp=alpha_cool, timer=ti,
)
cool.add_convection("pebble", h=h_cool, area=a_pb)
cool.add_advection("cool", m_flow / n_pebbles, t_inlet, cp=cool.cp)

components = []
for i in range(len(pebble.sub_comp)):
    components.append(pebble.sub_comp[i])
components.extend([pebble, cool])

uncert = [
    alpha_cool, alpha_fuel, k_mod, k_fuel, k_shell,
    cp_mod, cp_fuel, cp_shell, cp_cool, h_cool.h(),
]
uncertainty_param = np.array([o.magnitude for o in uncert])
