"""Scalar metrics of a simulation (pure NumPy). Used by the comparison table and the sweeps."""
import numpy as np

from . import core

METRICS = {  # key: (label, unit)
    "v1": ("Line-to-line fundamental (peak)", "V"),
    "m_eff": ("Effective modulation index", ""),
    "wthd": ("WTHD of v_AB", "%"),
    "thd": ("THD of v_AB", "%"),
    "i_rms": ("Load current, RMS", "A"),
    "i_ripple": ("Current ripple, RMS", "A"),
    "p_cond": ("Conduction losses", "W"),
    "p_sw": ("Switching losses", "W"),
    "p_loss": ("Total switch losses", "W"),
    "p_out": ("Output power", "W"),
    "eff": ("Efficiency (switches only)", "%"),
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


def summarize(s, load, vdc, dev=core.DEVICE, v_key="v_ab", n_legs=3, n_phases=3):
    """Metrics of a simulation result `s` (from core.three_phase & co) that includes the R-L load."""
    h, a = core.spectrum(s[v_key])
    thd, wthd = core.distortion(h, a)
    i = s["i_legs"][0]
    leg = core.leg_losses(s["poles"][0], i, load.f1, vdc, dev)
    p_cond = n_legs * sum(c for c, _ in leg.values())
    p_sw = n_legs * sum(w for _, w in leg.values())
    p_out = n_phases * load.R * float(np.mean(i**2))
    out = {"v1": float(a[1]), "thd": 100 * thd, "wthd": 100 * wthd, "i_rms": rms(i), "i_ripple": ripple_rms(i),
           "p_cond": p_cond, "p_sw": p_sw, "p_loss": p_cond + p_sw, "p_out": p_out,
           "eff": 100 * p_out / (p_out + p_cond + p_sw) if p_out > 0 else float("nan")}
    if "v_cm" in s:
        out["vcm_rms"], out["vcm_pk"] = rms(s["v_cm"]), float(np.abs(s["v_cm"]).max())
    return out


def three_phase_metrics(mod, ma, mf, vdc, load, dead=0, kind="Triangle", dev=core.DEVICE):
    s = core.three_phase(core.time_grid(), ma, mf, vdc, mod, load, dead, kind)
    m = summarize(s, load, vdc, dev)
    m["m_eff"] = m["v1"] / (np.sqrt(3) / 2 * vdc)  # 1 = the line-to-line amplitude SPWM gives at m_a = 1
    return m


def sweep(name, values, **fixed):
    """Run three_phase_metrics for every value of the keyword `name`. Returns {metric: array}."""
    rows = [three_phase_metrics(**{**fixed, name: v}) for v in values]
    return {k: np.array([r[k] for r in rows]) for k in rows[0]}