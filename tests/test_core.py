import numpy as np
import pytest

from pwmlab import core as c

T, V = c.time_grid(), 1.0


def amp(x, h):
    return c.spectrum(x)[1][h]


@pytest.mark.parametrize("ma", [0.3, 0.8, 1.0])
def test_half_bridge_fundamental(ma):
    assert amp(c.half_bridge(T, ma, 21, V)["v_a0"], 1) == pytest.approx(ma * V / 2, rel=1e-2)


@pytest.mark.parametrize("strategy", ["Unipolar", "Bipolar"])
def test_full_bridge_fundamental(strategy):
    assert amp(c.full_bridge(T, 0.8, 21, V, strategy)["v_ab"], 1) == pytest.approx(0.8 * V, rel=1e-2)


def test_bipolar_carrier_harmonic_matches_bessel_value():
    # (4/pi) * J0(pi*ma/2) at ma = 0.8 is 0.818 (textbook table value)
    assert amp(c.full_bridge(T, 0.8, 21, V, "Bipolar")["v_ab"], 21) == pytest.approx(0.818, rel=2e-2)


def test_unipolar_has_no_harmonic_at_fsw():
    assert amp(c.full_bridge(T, 0.8, 21, V, "Unipolar")["v_ab"], 21) < 1e-2


def test_three_phase_spwm_line_fundamental():
    assert amp(c.three_phase(T, 0.8, 21, V, "SPWM")["v_ab"], 1) == pytest.approx(np.sqrt(3) / 2 * 0.8, rel=1e-2)


@pytest.mark.parametrize("mod", ["Third-harmonic injection", "SVPWM"])
def test_injection_extends_linear_range(mod):
    ideal = np.sqrt(3) / 2 * 1.1
    assert amp(c.three_phase(T, 1.1, 21, V, mod)["v_ab"], 1) == pytest.approx(ideal, rel=1e-2)
    assert amp(c.three_phase(T, 1.1, 21, V, "SPWM")["v_ab"], 1) < 0.99 * ideal  # SPWM already saturates


def test_fsw_harmonic_is_common_mode_in_three_phase():
    s = c.three_phase(T, 0.8, 21, V, "SPWM")
    assert amp(s["v_ab"], 21) < 5e-3  # cancels line-to-line
    assert amp(s["v_cm"], 21) > 0.1  # but sits in the common-mode voltage


def test_load_current_limits():
    v = c.full_bridge(T, 0.8, 21, V)["v_ab"]
    assert np.allclose(c.load_current(v, 50, 10.0, 0.0), v / 10.0)  # L = 0: i = v / R
    assert np.mean(c.load_current(v, 50, 10.0, 0.02)) == pytest.approx(np.mean(v) / 10.0, abs=1e-9)
