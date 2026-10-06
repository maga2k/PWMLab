import numpy as np
import pytest

from pwmlab import core, metrics as M

LOAD = core.Load(50, 10.0, 0.02)


def run(mod, ma=0.8, mf=15, **kw):
    return M.three_phase_metrics(mod, ma, mf, 400.0, LOAD, **kw)


def test_ripple_removes_dc_and_fundamental_only():
    t = core.time_grid()
    assert M.ripple_rms(3 + 5 * np.sin(2 * np.pi * t)) < 1e-9
    assert M.ripple_rms(5 * np.sin(2 * np.pi * t) + 0.1 * np.sin(20 * np.pi * t)) == pytest.approx(0.1 / np.sqrt(2), rel=1e-6)


def test_current_ripple_scales_as_one_over_fsw():
    assert run("SPWM", mf=15)["i_ripple"] / run("SPWM", mf=45)["i_ripple"] == pytest.approx(3, rel=0.1)


def test_switching_losses_scale_with_fsw():
    assert run("SPWM", mf=45)["p_sw"] / run("SPWM", mf=15)["p_sw"] == pytest.approx(3, rel=0.1)


def test_efficiency_is_consistent_with_powers():
    m = run("SPWM")
    assert m["eff"] == pytest.approx(100 * m["p_out"] / (m["p_out"] + m["p_loss"]))
    assert m["p_loss"] == pytest.approx(m["p_cond"] + m["p_sw"])


def test_six_step_common_mode_is_vdc_over_six():
    m = run("Six-step")
    assert m["vcm_rms"] == pytest.approx(400 / 6, rel=1e-6) and m["vcm_pk"] == pytest.approx(400 / 6, rel=1e-6)


def test_effective_modulation_index():
    assert run("SPWM", ma=0.7)["m_eff"] == pytest.approx(0.7, rel=1e-2)
    assert run("SVPWM", ma=1.1)["m_eff"] == pytest.approx(1.1, rel=1e-2)
    assert run("SPWM", ma=1.1)["m_eff"] < 1.1 * 0.99  # SPWM already saturates
    assert run("Six-step")["m_eff"] == pytest.approx(4 / np.pi, rel=1e-3)


def test_dpwm_saves_switching_loss_but_not_common_mode():
    spwm, dpwm = run("SPWM", mf=39), run("DPWM1", mf=39)
    assert dpwm["p_sw"] < 0.85 * spwm["p_sw"]
    assert dpwm["vcm_rms"] == pytest.approx(spwm["vcm_rms"], rel=0.05)
    assert dpwm["wthd"] > spwm["wthd"]


def test_sweep_matches_individual_runs():
    fixed = dict(mod="SPWM", ma=0.8, vdc=400.0, load=LOAD, dead=0, kind="Triangle", dev=core.DEVICE)
    out = M.sweep("mf", [15, 45], **fixed)
    assert out["p_sw"][1] == pytest.approx(run("SPWM", mf=45)["p_sw"])
    assert out["wthd"].shape == (2,)

# ---------------------------------------------------------------- power quantities
def test_power_quantities_of_a_pure_sine_pair():
    t = core.time_grid()
    phi = 0.6
    q = M.power_quantities(10 * np.sin(2 * np.pi * t), 2 * np.sin(2 * np.pi * t - phi))
    assert q["p"] == pytest.approx(10 * np.cos(phi)) and q["q1"] == pytest.approx(10 * np.sin(phi))
    assert q["s"] == pytest.approx(10) and q["d"] < 1e-6
    assert q["pf"] == pytest.approx(np.cos(phi)) and q["dpf"] == pytest.approx(np.cos(phi)) and q["dist"] == pytest.approx(1)


def test_pwm_load_powers_match_the_rl_circuit():
    # an R-L load: P = R * I_rms^2 (all harmonics), Q1 = X * I1_rms^2, cos(phi1) = R / |Z|
    s = core.three_phase(core.time_grid(), 0.8, 21, 400.0, "SPWM", LOAD)
    q = M.power_quantities(s["v_abc"], s["i_legs"])
    x = 2 * np.pi * LOAD.f1 * LOAD.L
    i1 = sum((2 * np.abs(np.fft.rfft(ik)[1]) / core.N) ** 2 / 2 for ik in s["i_legs"])  # sum of I1_rms^2
    assert q["p"] == pytest.approx(LOAD.R * np.sum(np.mean(s["i_legs"] ** 2, axis=1)), rel=1e-9)
    assert q["q1"] == pytest.approx(x * i1, rel=1e-6)
    assert q["dpf"] == pytest.approx(LOAD.R / np.hypot(LOAD.R, x), rel=1e-6)
    assert q["s"] ** 2 == pytest.approx(q["p"] ** 2 + q["q1"] ** 2 + q["d"] ** 2) and 0 < q["pf"] < q["dpf"] <= 1


def test_summarize_power_equals_output_power():
    m = run("SVPWM")
    assert m["s_app"] >= np.hypot(m["p_out"], m["q1"]) and 0 < m["pf"] <= m["dpf"]
    for dead in (0, core.dead_samples(5, 50)):
        m = run("SPWM", dead=dead)
        s = core.three_phase(core.time_grid(), 0.8, 15, 400.0, "SPWM", LOAD, dead)
        assert M.power_quantities(s["v_abc"], s["i_legs"])["p"] == pytest.approx(m["p_out"], rel=1e-9)


def test_regular_sampling_is_accepted_by_the_metrics():
    assert run("SPWM", mf=15, sampling="Symmetric")["wthd"] != run("SPWM", mf=15)["wthd"]


def test_current_distortion_factor():
    t = core.time_grid()
    assert M.power_quantities(10 * np.sin(2 * np.pi * t), 2 * np.sin(2 * np.pi * t - 0.3))["i_dist"] == pytest.approx(1)
    one = M.power_quantities(np.sin(2 * np.pi * t), np.sin(2 * np.pi * t) + 0.5 * np.sin(6 * np.pi * t))
    assert one["i_dist"] == pytest.approx(1 / np.sqrt(1.25))  # I1 / sqrt(I1^2 + I3^2)
    m = run("SPWM", mf=39)
    assert m["i_dist"] > 0.995 and m["dist"] < 0.8  # clean current, distorted voltage


# ---------------------------------------------------------------- single-phase cases and thermal metrics
def sp(case, ma=0.8, mf=39, **kw):
    return M.single_phase_metrics(case, ma, mf, 400.0, LOAD, **kw)


def test_parse_case():
    assert M.parse_case("Half bridge \u00b7 Triangle") == ("Half bridge", None, "Triangle")
    assert M.parse_case("Full bridge \u00b7 Unipolar \u00b7 Sawtooth rising") == ("Full bridge", "Unipolar", "Sawtooth rising")
    assert len(M.SINGLE_PHASE_CASES) == 9


def test_single_phase_fundamental_and_output_power():
    for case in M.SINGLE_PHASE_CASES:
        m = sp(case)
        assert m["m_eff"] == pytest.approx(0.8, rel=1e-2)
        assert m["p_out"] == pytest.approx(LOAD.R * m["i_rms"] ** 2, rel=1e-9)  # one phase: P = R * I_rms^2


def test_full_bridge_doubles_the_half_bridge_voltage_and_ripple():
    half, full = sp("Half bridge \u00b7 Triangle"), sp("Full bridge \u00b7 Bipolar \u00b7 Triangle")
    assert full["v1"] == pytest.approx(2 * half["v1"], rel=1e-2)
    assert full["i_ripple"] == pytest.approx(2 * half["i_ripple"], rel=0.05)
    assert full["wthd"] == pytest.approx(half["wthd"], rel=0.02)  # same waveform shape


def test_unipolar_moves_the_dominant_harmonic_to_twice_fsw_and_cuts_the_ripple():
    bip, uni = sp("Full bridge \u00b7 Bipolar \u00b7 Triangle"), sp("Full bridge \u00b7 Unipolar \u00b7 Triangle")
    saw = sp("Full bridge \u00b7 Unipolar \u00b7 Sawtooth rising")
    assert bip["h_dom"] == pytest.approx(1.0, abs=0.05) and uni["h_dom"] == pytest.approx(2.0, abs=0.1)
    assert saw["h_dom"] == pytest.approx(1.0, abs=0.1)  # the doubling is lost
    assert uni["i_ripple"] < 0.35 * bip["i_ripple"] and saw["i_ripple"] > 1.7 * uni["i_ripple"]
    assert uni["p_sw"] == pytest.approx(bip["p_sw"], rel=0.05)  # same switching losses


def test_case_metrics_dispatches_to_both_families():
    a = M.case_metrics("Three-phase", "SVPWM", 0.8, 15, 400.0, LOAD)
    assert a["wthd"] == pytest.approx(run("SVPWM")["wthd"])
    b = M.case_metrics("Single-phase", "Half bridge \u00b7 Triangle", 0.8, 39, 400.0, LOAD)
    assert b["wthd"] == pytest.approx(sp("Half bridge \u00b7 Triangle")["wthd"]) and "vcm_rms" not in b


def test_case_sweep_matches_individual_runs():
    out = M.case_sweep("Single-phase", "Full bridge \u00b7 Unipolar \u00b7 Triangle", "mf", [15, 45], ma=0.8, vdc=400.0, load=LOAD)
    assert out["i_ripple"][1] == pytest.approx(sp("Full bridge \u00b7 Unipolar \u00b7 Triangle", mf=45)["i_ripple"])


def test_thermal_metrics():
    th = dict(core.THERMAL)
    m = run("SPWM", mf=39, thermal=th)
    assert m["t_hs"] == pytest.approx(th["t_amb"] + th["r_sa"] * m["p_loss"])
    assert m["tj_peak"] > m["t_hs"] and m["tj_swing"] > 0
    hi = run("SPWM", mf=199, thermal=th)
    assert hi["tj_peak"] > m["tj_peak"] and "t_hs" not in run("SPWM", mf=39)  # only computed on request
    assert run("DPWM2", mf=199, thermal=th)["tj_peak"] < hi["tj_peak"]  # fewer switchings run cooler