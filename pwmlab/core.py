"""Core PWM maths. Pure NumPy, no Streamlit, so it can be tested and reused.

Assumptions: ideal switches, stiff DC bus Vdc, voltages are referred to the DC midpoint,
time is normalised to one fundamental period (0 <= t < 1), carrier spans -1..+1.
"""
import numpy as np

N = 2**15  #samples per fundamental period


def time_grid(n=N):
    return np.arange(n) / n


def carrier(t, mf):
    """Centre-aligned triangle between -1 and +1 (peak at t = 0)."""
    return 4 * np.abs((t * mf) % 1 - 0.5) - 1


def sine(t, ma, phase=0.0):
    return ma * np.sin(2 * np.pi * t - phase)


def pole(ref, car, vdc):
    """Ideal half-bridge pole voltage: +Vdc/2 when reference > carrier, else -Vdc/2."""
    return np.where(ref > car, vdc / 2, -vdc / 2)


#Topologies
def half_bridge(t, ma, mf, vdc):
    ref, car = sine(t, ma), carrier(t, mf)
    return {"ref": ref, "car": car, "v_a0": pole(ref, car, vdc)}


def full_bridge(t, ma, mf, vdc, strategy="Unipolar"):
    ref, car = sine(t, ma), carrier(t, mf)
    va = pole(ref, car, vdc)
    if strategy == "Bipolar":  #leg B is the complement of leg A
        ref_b, vb = None, -va
    else:  #unipolar: leg B uses the inverted reference, same carrier
        ref_b = -ref
        vb = pole(ref_b, car, vdc)
    return {"ref": ref, "ref_b": ref_b, "car": car, "v_a0": va, "v_b0": vb, "v_ab": va - vb}


MODULATIONS = ["SPWM", "Third-harmonic injection", "SVPWM", "DPWM-MAX", "DPWM-MIN"]


def three_phase_refs(t, ma, mod):
    r = np.array([sine(t, ma, k * 2 * np.pi / 3) for k in range(3)])
    if mod == "SPWM":
        return r
    if mod.startswith("Third"):
        return r + ma * np.sin(6 * np.pi * t) / 6  # 1/6 of the 3rd harmonic
    if mod == "SVPWM":
        return r - (r.max(0) + r.min(0)) / 2  #min-max (zero-sequence) injection
    if mod == "DPWM-MAX":
        return r + (1 - r.max(0))  #highest phase clamped to +1
    if mod == "DPWM-MIN":
        return r - (1 + r.min(0))  #lowest phase clamped to -1
    raise ValueError(mod)


def three_phase(t, ma, mf, vdc, mod="SPWM"):
    refs, car = three_phase_refs(t, ma, mod), carrier(t, mf)
    p = pole(refs, car, vdc)
    vcm = p.mean(0)  #common-mode voltage of a balanced star load
    return {"refs": refs, "car": car, "poles": p, "v_ab": p[0] - p[1], "v_an": p[0] - vcm, "v_cm": vcm}


#Analysis
def spectrum(x):
    """Peak amplitude of each harmonic of the fundamental. x must be exactly one period."""
    X = np.fft.rfft(x) / len(x)
    amp = 2 * np.abs(X)
    amp[0] = np.abs(X[0])
    return np.arange(len(amp)), amp


def distortion(h, amp):
    """(THD, WTHD) relative to the fundamental; NaN if there is no fundamental."""
    if amp[1] < 1e-9:
        return float("nan"), float("nan")
    thd = np.sqrt(np.sum(amp[2:] ** 2)) / amp[1]
    wthd = np.sqrt(np.sum((amp[2:] / h[2:]) ** 2)) / amp[1]
    return thd, wthd


def load_current(v, f1, R, L):
    """Periodic steady-state current of a series R-L load (no start-up transient), via I_h = V_h / Z_h."""
    V = np.fft.rfft(v)
    h = np.arange(len(V))
    return np.fft.irfft(V / (R + 1j * 2 * np.pi * f1 * h * L), n=len(v))
