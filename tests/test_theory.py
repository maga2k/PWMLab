import xml.etree.ElementTree as ET

import numpy as np
import pytest

from pwmlab import core as c, schematics, theory

T = c.time_grid()


def amp(x, h):
    return c.spectrum(x)[1][h]


def test_bessel_known_values():
    assert theory.bessel_j(0, 0) == pytest.approx(1) and theory.bessel_j(1, 0) == pytest.approx(0, abs=1e-12)
    assert theory.bessel_j(0, 1) == pytest.approx(0.7651976866, abs=1e-9)
    assert theory.bessel_j(1, 1) == pytest.approx(0.4400505857, abs=1e-9)
    assert theory.bessel_j(0, 2.404825557695773) == pytest.approx(0, abs=1e-9)  # first zero of J0
    assert theory.bessel_j(-1, 1.3) == pytest.approx(-theory.bessel_j(1, 1.3))
    assert theory.bessel_j(-2, 1.3) == pytest.approx(theory.bessel_j(2, 1.3))


@pytest.mark.parametrize("ma, mf", [(0.8, 21), (0.5, 15), (1.0, 31)])
def test_triangle_harmonic_formula_matches_the_simulation(ma, mf):
    vdc = 400.0
    sim = c.spectrum(c.half_bridge(T, ma, mf, vdc)["v_a0"])[1]
    for h, a in theory.triangle_harmonics(ma, mf, vdc).items():
        assert sim[h] == pytest.approx(a, abs=0.003 * vdc)
    # the orders the formula says are empty (m + n even) are empty in the simulation
    for h in (mf - 3, mf - 1, mf + 1, mf + 3, 2 * mf - 2, 2 * mf, 2 * mf + 2):
        assert sim[h] < 0.002 * vdc


def test_dead_time_puts_5th_7th_harmonics_in_the_phase_voltage_with_one_over_h_amplitude():
    load = c.Load(50, 10.0, 0.02)
    clean = c.spectrum(c.three_phase(T, 0.8, 39, 400.0, "SPWM", load)["v_an"])[1]
    dead = c.spectrum(c.three_phase(T, 0.8, 39, 400.0, "SPWM", load, c.dead_samples(5, 50))["v_an"])[1]
    assert clean[5] / clean[1] < 5e-4 and dead[5] / dead[1] > 4e-3
    assert dead[5] * 5 == pytest.approx(dead[7] * 7, rel=0.1)  # amplitude proportional to 1/h
    assert dead[7] * 7 == pytest.approx(dead[11] * 11, rel=0.25)


def test_dead_time_fundamental_drop_follows_the_formula():
    load = c.Load(50, 10.0, 0.02)
    dead = c.dead_samples(5, 50)
    v0 = amp(c.three_phase(T, 0.8, 39, 400.0, "SPWM", load)["v_an"], 1)
    v1 = amp(c.three_phase(T, 0.8, 39, 400.0, "SPWM", load, dead)["v_an"], 1)
    e = theory.dead_time_fundamental(400.0, dead / (50 * c.N), 39 * 50)
    cos_phi = 10 / np.hypot(10, 2 * np.pi * 50 * 0.02)
    assert v0 - v1 == pytest.approx(e * cos_phi, rel=0.1)  # the error is in phase with the current


@pytest.mark.parametrize("mod, levels", [("SPWM", [-1 / 2, -1 / 6, 1 / 6, 1 / 2]), ("SVPWM", [-1 / 2, -1 / 6, 1 / 6, 1 / 2]),
                                         ("DPWM1", [-1 / 2, -1 / 6, 1 / 6, 1 / 2]), ("Six-step", [-1 / 6, 1 / 6])])
def test_common_mode_voltage_takes_only_a_few_values(mod, levels):
    vcm = c.three_phase(T, 0.8, 21, 400.0, mod)["v_cm"] / 400.0
    assert np.allclose(np.unique(np.round(vcm, 4)), levels, atol=1e-3)


def test_thermal_attenuation_matches_the_junction_model():
    for f1, tau in ((5, 0.01), (50, 0.01), (400, 0.002)):
        tj = c.junction_temperature(30 * np.sin(2 * np.pi * T), 0.9, tau, 60.0, f1)
        assert tj.max() - tj.min() == pytest.approx(2 * 30 * 0.9 * theory.thermal_attenuation(f1, tau), rel=1e-6)


@pytest.mark.parametrize("name", ["half_bridge", "full_bridge", "three_phase", "modulator", "hexagon", "thermal_network"])
def test_schematics_are_well_formed_svg(name):
    svg = getattr(schematics, name)()
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg") and "\n\n" not in svg