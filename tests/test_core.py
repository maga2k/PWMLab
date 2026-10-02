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

def test_gates_are_complementary_and_balanced():
    up, lo = c.gates(c.half_bridge(T, 0.8, 21, V)["v_a0"])
    assert np.all(up + lo == 1)
    assert up.mean() == pytest.approx(0.5, abs=1e-3)  # sine reference: average duty is 50 %


# ---------------------------------------------------------------- dead time
LOAD = c.Load(50, 10.0, 0.05)


def test_dead_time_never_overlaps_and_matches_gap_fraction():
    dead, mf = c.dead_samples(10, 50), 99
    s = c.half_bridge(T, 0.5, mf, V, LOAD, dead)
    up, lo = s["gate_up"][0], s["gate_lo"][0]
    assert np.max(up * lo) == 0
    assert 1 - (up + lo).mean() == pytest.approx(2 * dead * mf / c.N, rel=1e-6)  # two gaps per carrier period


def test_zero_dead_time_is_the_ideal_converter():
    ideal = c.half_bridge(T, 0.8, 21, V)
    s = c.half_bridge(T, 0.8, 21, V, LOAD, 0)
    assert np.array_equal(ideal["v_a0"], s["v_a0"])


def test_dead_time_pole_voltage_is_self_consistent_with_the_current():
    s = c.half_bridge(T, 0.9, 99, V, LOAD, c.dead_samples(10, 50))
    again = c.pole_from_gates(s["gate_up"], s["gate_lo"], s["i_legs"], V)
    assert np.mean(again != s["poles"]) < 1e-3


def test_dead_time_fundamental_matches_the_phasor_estimate():
    ma, mf, td = 0.9, 99, 10
    dead = c.dead_samples(td, 50)
    A = ma * V / 2
    e = 4 / np.pi * dead / (50 * c.N) * 50 * mf * V      # fundamental of the +-Vdc*td*fsw error square wave
    phi = np.arctan(2 * np.pi * 50 * LOAD.L / LOAD.R)    # current lags the voltage
    v = complex(A)
    for _ in range(200):                                  # the error follows the current, which follows v
        v = A - e * np.exp(1j * (np.angle(v) - phi))
    got = amp(c.half_bridge(T, ma, mf, V, LOAD, dead)["v_a0"], 1)
    assert got < amp(c.half_bridge(T, ma, mf, V, LOAD, 0)["v_a0"], 1)
    assert got == pytest.approx(abs(v), rel=1e-2)


def test_three_phase_currents_sum_to_zero_with_dead_time():
    s = c.three_phase(T, 0.8, 21, V, "SPWM", c.Load(50, 10.0, 0.02), c.dead_samples(5, 50))
    assert np.abs(s["i_legs"].sum(0)).max() < 1e-9


# ---------------------------------------------------------------- losses
def test_conduction_losses_add_up_to_r_i_squared():
    s = c.half_bridge(T, 0.8, 21, 400.0, LOAD, c.dead_samples(5, 50))
    dev = dict(c.DEVICE, vce0=0, vf0=0, rce=0.02, rd=0.02, eon=0, eoff=0, err=0)
    leg = c.leg_losses(s["poles"][0], s["i_legs"][0], 50, 400.0, dev)
    assert sum(cnd for cnd, _ in leg.values()) == pytest.approx(0.02 * np.mean(s["i_legs"][0] ** 2), rel=1e-9)


def test_switching_losses_scale_with_dc_voltage():
    s = c.half_bridge(T, 0.8, 21, 400.0, LOAD, 0)
    a = c.leg_losses(s["poles"][0], s["i_legs"][0], 50, 400.0)
    b = c.leg_losses(s["poles"][0], s["i_legs"][0], 50, 800.0)
    assert sum(w for _, w in b.values()) == pytest.approx(2 * sum(w for _, w in a.values()))


def test_dpwm_switches_less_than_spwm():
    load = c.Load(50, 10.0, 0.02)
    sw = {}
    for mod in ["SPWM", "DPWM-MAX"]:
        s = c.three_phase(T, 0.8, 21, 400.0, mod, load)
        sw[mod] = sum(w for _, w in c.leg_losses(s["poles"][0], s["i_legs"][0], 50, 400.0).values())
    assert sw["DPWM-MAX"] < 0.8 * sw["SPWM"]


    # ---------------------------------------------------------------- carriers
def edges(g):
    """Sample indices of rising and falling edges of a 0/1 signal (circular)."""
    prev = np.roll(g, 1)
    return np.flatnonzero((g == 1) & (prev == 0)), np.flatnonzero((g == 0) & (prev == 1))


def test_carrier_shapes():
    t = np.array([0, 0.0625, 0.125, 0.1875])  # with mf = 4: position in the carrier period is 0, 1/4, 1/2, 3/4
    assert np.allclose(c.carrier(t, 4, "Triangle"), [1, 0, -1, 0])
    assert np.allclose(c.carrier(t, 4, "Sawtooth rising"), [-1, -0.5, 0, 0.5])
    assert np.allclose(c.carrier(t, 4, "Sawtooth falling"), [1, 0.5, 0, -0.5])


@pytest.mark.parametrize("kind", ["Sawtooth rising", "Sawtooth falling"])
def test_sawtooth_fundamental_is_unchanged(kind):
    assert amp(c.half_bridge(T, 0.8, 21, V, kind=kind)["v_a0"], 1) == pytest.approx(0.4, rel=1e-2)


@pytest.mark.parametrize("kind, locked", [("Sawtooth rising", 0), ("Sawtooth falling", 1)])
def test_sawtooth_locks_one_edge_to_the_carrier_period(kind, locked):
    mf = 21
    g = c.half_bridge(T, 0.8, mf, V, kind=kind)["gate_up"][0]
    expected = np.ceil(np.arange(mf) * c.N / mf)
    fixed, moving = edges(g)[locked], edges(g)[1 - locked]
    assert len(fixed) == len(moving) == mf
    assert np.max(np.abs(fixed - expected)) <= 1  # rising saw: rising edge fixed; falling saw: falling edge fixed
    assert np.max(np.abs(moving - expected)) > 100  # the other edge follows the reference


def test_sawtooth_adds_odd_sidebands_and_carrier_second_harmonic():
    mf = 21
    tri = c.half_bridge(T, 0.8, mf, V)["v_a0"]
    saw = c.half_bridge(T, 0.8, mf, V, kind="Sawtooth rising")["v_a0"]
    for h in (mf - 1, 2 * mf):
        assert amp(tri, h) < 1e-3
        assert amp(saw, h) > 0.05


def test_unipolar_loses_frequency_doubling_with_sawtooth():
    mf = 21
    low = lambda kind: c.spectrum(c.full_bridge(T, 0.8, mf, V, "Unipolar", kind=kind)["v_ab"])[1][2:int(1.5 * mf)].max()
    assert low("Triangle") < 1e-2          # nothing below ~2 f_sw
    assert low("Sawtooth rising") > 0.1    # first group is back around f_sw


# ---------------------------------------------------------------- DPWM family and six-step
CLAMPED = ["DPWM0", "DPWM1", "DPWM2", "DPWM-MAX", "DPWM-MIN"]


@pytest.mark.parametrize("mod", CLAMPED)
def test_dpwm_keeps_each_phase_on_a_rail_for_about_a_third_of_the_period(mod):
    # DPWM0/2 hold the clamp decision per carrier period, so a reference may touch the rail slightly longer
    r = c.three_phase_refs(T, 0.8, mod, 21)
    assert np.mean(np.abs(r) >= 1 - 1e-9, axis=1) == pytest.approx([1 / 3] * 3, abs=0.015)


@pytest.mark.parametrize("mod", ["Third-harmonic injection", "SVPWM", "DPWM1", "DPWM-MAX", "DPWM-MIN"])
def test_references_stay_inside_the_carrier_up_to_1155(mod):
    assert np.abs(c.three_phase_refs(T, 1.15, mod, 21)).max() <= 1 + 1e-9


@pytest.mark.parametrize("mod", ["Third-harmonic injection", "SVPWM"] + CLAMPED)
@pytest.mark.parametrize("mf", [21, 45])
def test_zero_sequence_modulations_keep_the_linear_fundamental(mod, mf):
    for ma in (0.8, 1.15):
        v = c.three_phase(T, ma, mf, V, mod)["v_ab"]
        assert amp(v, 1) == pytest.approx(np.sqrt(3) / 2 * ma, rel=1e-2)


def test_clamped_leg_skips_a_third_of_its_switchings():
    for g in c.three_phase(T, 0.8, 21, V, "DPWM1")["gate_up"]:
        assert abs(len(edges(g)[0]) - 14) <= 1  # 21 carrier periods, 2/3 of them active


def test_best_clamp_window_follows_the_current_peak():
    L = 10 * np.tan(np.pi / 6) / (2 * np.pi * 50)  # current lags the voltage by 30 degrees
    sw = {}
    for mod in ["DPWM0", "DPWM1", "DPWM2"]:
        s = c.three_phase(T, 0.8, 39, 400.0, mod, c.Load(50, 10.0, L))
        sw[mod] = sum(w for _, w in c.leg_losses(s["poles"][0], s["i_legs"][0], 50, 400.0).values())
    assert sw["DPWM2"] < 0.9 * sw["DPWM1"] < sw["DPWM0"]


def test_six_step_matches_textbook_values():
    s = c.three_phase(T, 0.8, 21, 400.0, "Six-step")
    a = c.spectrum(s["v_ab"])[1]
    assert a[1] == pytest.approx(2 * np.sqrt(3) / np.pi * 400, rel=1e-3)
    assert a[3] < 1e-3 * a[1]
    assert a[5] / a[1] == pytest.approx(1 / 5, rel=1e-2)
    assert a[7] / a[1] == pytest.approx(1 / 7, rel=1e-2)
    assert c.distortion(*c.spectrum(s["v_an"]))[0] == pytest.approx(np.sqrt(np.pi**2 / 9 - 1), rel=1e-2)
    assert np.allclose(np.unique(np.round(s["v_an"] / 400, 3)), [-2 / 3, -1 / 3, 1 / 3, 2 / 3], atol=1e-3)
    d, q = c.park(*c.clarke(s["v_abc"]), T)
    assert d.mean() == pytest.approx(2 / np.pi * 400, rel=1e-3) and abs(q.mean()) < 0.5


# ---------------------------------------------------------------- Clarke / Park
def test_clarke_park_of_a_balanced_set():
    x = np.array([c.sine(T, 3.0, k * 2 * np.pi / 3) for k in range(3)])
    al, be = c.clarke(x)
    d, q = c.park(al, be, T)
    assert np.allclose(np.hypot(al, be), 3.0)
    assert np.allclose(d, 3.0) and np.allclose(q, 0, atol=1e-9)


def test_zero_sequence_injection_is_invisible_in_alpha_beta():
    base = c.clarke(c.three_phase_refs(T, 0.8, "SPWM"))
    for mod in ["Third-harmonic injection", "SVPWM"] + CLAMPED:
        assert np.allclose(c.clarke(c.three_phase_refs(T, 0.8, mod)), base, atol=1e-9)


def test_lagging_current_has_negative_q_component():
    s = c.three_phase(T, 0.8, 21, 400.0, "SPWM", c.Load(50, 10.0, 0.02))
    d, q = c.park(*c.clarke(s["i_legs"]), T)
    phi = np.arctan(2 * np.pi * 50 * 0.02 / 10)
    assert q.mean() / d.mean() == pytest.approx(-np.tan(phi), rel=2e-2)


def test_carrier_average_recovers_the_reference():
    h = c.half_bridge(T, 0.8, 21, 400.0)
    assert np.max(np.abs(c.carrier_average(h["v_a0"], 21) - h["ref"] * 200)) < 0.05 * 400
    assert np.allclose(c.carrier_average(np.ones(c.N), 21), 1)