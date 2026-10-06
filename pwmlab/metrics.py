"""Scalar metrics of a simulation (pure NumPy). Used by the comparison table and the sweeps."""
import numpy as np

from . import core

METRICS = {  # key: (label, unit)
    "v1": ("Line-to-line fundamental (peak)", "V"),
    "m_eff": ("Effective modulation index", "p.u."),
    "wthd": ("WTHD of v_AB", "%"),
    "thd": ("THD of v_AB", "%"),
    "i_rms": ("Load current, RMS", "A"),
    "i_ripple": ("Current ripple, RMS", "A"),
    "p_cond": ("Conduction losses", "W"),
    "p_sw": ("Switching losses", "W"),
    "p_loss": ("Total switch losses", "W"),
    "p_out": ("Output power", "W"),
    "eff": ("Efficiency (switches only)", "%"),
    "q1": ("Reactive power Q1 (fundamental)", "var"),
    "s_app": ("Apparent power S", "VA"),
    "d_pow": ("Distortion power D", "VA"),
    "pf": ("Power factor P/S", "-"),
    "dpf": ("Displacement factor cos(phi1)", "-"),
    "dist": ("Distortion factor S1/S", "-"),
    "i_dist": ("Current distortion factor I1/I_rms", "-"),
    "h_dom": ("Dominant harmonic", "x f_sw"),
    "t_hs": ("Heatsink temperature", "\u00b0C"),
    "tj_peak": ("Hottest junction, peak", "\u00b0C"),
    "tj_swing": ("Junction swing, hottest device", "K"),
    "vcm_rms": ("Common-mode voltage, RMS", "V"),
    "vcm_pk": ("Common-mode voltage, peak", "V"),
}


def rms(x):
    return float(np.sqrt(np.mean(np.square(x))))


def ripple_rms(i):
    """RMS of the current once its DC and fundamental components are removed."""
    spec = np.fft.rfft(i)
    keep = np.zeros_like(spec)
    keep[:2] = spec[:2]
    return rms(i - np.fft.irfft(keep, n=len(i)))


def power_quantities(v, i):
    """Powers of a load fed by periodic voltages v and currents i, shape (phases, N), exactly one
    fundamental period. Everything is summed over the phases.

    P: mean of v*i. S: sum of V_rms * I_rms. Q1: fundamental reactive power (positive when the current
    lags). D: distortion power, S^2 = P^2 + Q1^2 + D^2. Displacement factor: cos(phi1) = P1 / S1 of the
    fundamentals. Distortion factor: S1 / S, so PF = P/S is close to their product. At the output of a
    PWM inverter S is dominated by the voltage harmonics, so S1/S and PF are low even for a clean current:
    i_dist = I1 / I_rms is the distortion factor of the current alone."""
    v, i = np.atleast_2d(v), np.atleast_2d(i)
    n = v.shape[1]
    p = float(np.sum(np.mean(v * i, axis=1)))
    s = float(np.sum(np.sqrt(np.mean(v**2, axis=1) * np.mean(i**2, axis=1))))
    v1, i1 = 2 * np.fft.rfft(v, axis=1)[:, 1] / n, 2 * np.fft.rfft(i, axis=1)[:, 1] / n  # peak phasors
    s1c = 0.5 * np.sum(v1 * np.conj(i1))  # P1 + jQ1
    s1 = float(0.5 * np.sum(np.abs(v1) * np.abs(i1)))
    i_sq = float(np.sum(np.mean(i**2, axis=1)))
    nan = float("nan")
    return {"p": p, "q1": float(s1c.imag), "s": s, "d": float(np.sqrt(max(s**2 - p**2 - s1c.imag**2, 0.0))),
            "pf": p / s if s > 0 else nan, "dpf": float(s1c.real) / s1 if s1 > 0 else nan,
            "dist": s1 / s if s > 0 else nan,
            "i_dist": float(np.sqrt(0.5 * np.sum(np.abs(i1) ** 2) / i_sq)) if i_sq > 0 else nan}


def summarize(s, load, vdc, dev=core.DEVICE, v_key="v_ab", n_legs=3, n_phases=3, vload_key="v_abc", thermal=None):
    """Metrics of a simulation result `s` (from core.three_phase & co) that includes the R-L load."""
    h, a = core.spectrum(s[v_key])
    thd, wthd = core.distortion(h, a)
    i = s["i_legs"][0]
    leg = core.leg_losses(s["poles"][0], i, load.f1, vdc, dev)
    p_cond = n_legs * sum(c for c, _ in leg.values())
    p_sw = n_legs * sum(w for _, w in leg.values())
    p_out = load.R * float(np.sum(np.mean(s["i_legs"][:n_phases] ** 2, axis=1)))  # sum over the phases
    out = {"v1": float(a[1]), "thd": 100 * thd, "wthd": 100 * wthd, "i_rms": rms(i), "i_ripple": ripple_rms(i),
           "p_cond": p_cond, "p_sw": p_sw, "p_loss": p_cond + p_sw, "p_out": p_out,
           "eff": 100 * p_out / (p_out + p_cond + p_sw) if p_out > 0 else float("nan")}
    pq = power_quantities(s[vload_key], s["i_legs"][:n_phases])
    out.update(q1=pq["q1"], s_app=pq["s"], d_pow=pq["d"], pf=pq["pf"], dpf=pq["dpf"], dist=pq["dist"],
               i_dist=pq["i_dist"])
    if "v_cm" in s:
        out["vcm_rms"], out["vcm_pk"] = rms(s["v_cm"]), float(np.abs(s["v_cm"]).max())
    if thermal is not None:
        th = core.thermal_analysis(core.leg_power_waveforms(s["poles"][0], i, load.f1, vdc, dev), n_legs, load.f1, thermal)
        hot = max(th["devices"].values(), key=lambda d: d["tj_peak"])
        out.update(t_hs=th["t_hs"], tj_peak=hot["tj_peak"], tj_swing=hot["tj_swing"])
    return out


def three_phase_metrics(mod, ma, mf, vdc, load, dead=0, kind="Triangle", dev=core.DEVICE, sampling="Natural",
                        thermal=None):
    s = core.three_phase(core.time_grid(), ma, mf, vdc, mod, load, dead, kind, sampling)
    m = summarize(s, load, vdc, dev, thermal=thermal)
    m["m_eff"] = m["v1"] / (np.sqrt(3) / 2 * vdc)  # 1 = the line-to-line amplitude SPWM gives at m_a = 1
    return m

def sweep(name, values, **fixed):
    """Run three_phase_metrics for every value of the keyword `name`. Returns {metric: array}."""
    rows = [three_phase_metrics(**{**fixed, name: v}) for v in values]
    return {k: np.array([r[k] for r in rows]) for k in rows[0]}

# ---------------------------------------------------------------- single-phase cases
SINGLE_PHASE_CASES = ([f"Half bridge \u00b7 {k}" for k in core.CARRIERS] +
                      [f"Full bridge \u00b7 {s} \u00b7 {k}" for s in ("Bipolar", "Unipolar") for k in core.CARRIERS])


def parse_case(case):
    """'Full bridge \u00b7 Unipolar \u00b7 Triangle' -> ('Full bridge', 'Unipolar', 'Triangle')."""
    parts = case.split(" \u00b7 ")
    return parts[0], (parts[1] if parts[0] == "Full bridge" else None), parts[-1]


def single_phase_metrics(case, ma, mf, vdc, load, dead=0, dev=core.DEVICE, sampling="Natural", thermal=None):
    """Metrics of a half-bridge or full-bridge case; the carrier (and for the full bridge the strategy) is
    part of the case. m_eff is the fundamental over V_dc/2 (half bridge) or V_dc (full bridge)."""
    topology, strategy, kind = parse_case(case)
    t = core.time_grid()
    if topology == "Half bridge":
        s, v_key, n_legs, scale = core.half_bridge(t, ma, mf, vdc, load, dead, kind, sampling), "v_a0", 1, vdc / 2
    else:
        s, v_key, n_legs, scale = core.full_bridge(t, ma, mf, vdc, strategy, load, dead, kind, sampling), "v_ab", 2, vdc
    out = summarize(s, load, vdc, dev, v_key=v_key, n_legs=n_legs, n_phases=1, vload_key=v_key, thermal=thermal)
    h, a = core.spectrum(s[v_key])
    out["m_eff"] = out["v1"] / scale
    out["h_dom"] = float(h[2:][np.argmax(a[2:])]) / mf  # order of the strongest harmonic, in carrier frequencies
    return out


def case_metrics(topology, case, ma, mf, vdc, load, dead=0, kind="Triangle", dev=core.DEVICE, sampling="Natural",
                 thermal=None):
    """One entry point for both families. topology: 'Three-phase' (case = modulation) or 'Single-phase'."""
    if topology == "Three-phase":
        return three_phase_metrics(case, ma, mf, vdc, load, dead, kind, dev, sampling, thermal)
    return single_phase_metrics(case, ma, mf, vdc, load, dead, dev, sampling, thermal)


def case_sweep(topology, case, name, values, **fixed):
    """case_metrics for every value of the keyword `name` (ma or mf); `fixed` holds the other keywords."""
    rows = [case_metrics(topology, case, **{**fixed, name: v}) for v in values]
    return {k: np.array([r[k] for r in rows]) for k in rows[0]}