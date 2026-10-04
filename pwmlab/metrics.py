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


def summarize(s, load, vdc, dev=core.DEVICE, v_key="v_ab", n_legs=3, n_phases=3, vload_key="v_abc"):
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
    return out


def three_phase_metrics(mod, ma, mf, vdc, load, dead=0, kind="Triangle", dev=core.DEVICE, sampling="Natural"):
    s = core.three_phase(core.time_grid(), ma, mf, vdc, mod, load, dead, kind, sampling)
    m = summarize(s, load, vdc, dev)
    m["m_eff"] = m["v1"] / (np.sqrt(3) / 2 * vdc)  # 1 = the line-to-line amplitude SPWM gives at m_a = 1
    return m

def sweep(name, values, **fixed):
    """Run three_phase_metrics for every value of the keyword `name`. Returns {metric: array}."""
    rows = [three_phase_metrics(**{**fixed, name: v}) for v in values]
    return {k: np.array([r[k] for r in rows]) for k in rows[0]}