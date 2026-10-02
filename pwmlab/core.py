"""Core PWM maths. Pure NumPy, no Streamlit, so it can be tested and reused.

Assumptions: ideal switches, stiff DC bus Vdc, voltages are referred to the DC midpoint,
time is normalised to one fundamental period (0 <= t < 1), carrier spans -1..+1.
"""
import numpy as np
from collections import namedtuple

N = 2**15  #samples per fundamental period


def time_grid(n=N):
    return np.arange(n) / n


CARRIERS = ["Triangle", "Sawtooth rising", "Sawtooth falling"]


def carrier(t, mf, kind="Triangle"):
    """Carrier between -1 and +1. Triangle: centre-aligned, peak at t = 0 (double-edge modulation).
    Sawtooth: one edge is locked to the start of every carrier period, only the other one moves."""
    x = (t * mf) % 1
    if kind == "Sawtooth rising":
        return 2 * x - 1
    if kind == "Sawtooth falling":
        return 1 - 2 * x
    return 4 * np.abs(x - 0.5) - 1


def sine(t, ma, phase=0.0):
    return ma * np.sin(2 * np.pi * t - phase)


def pole(ref, car, vdc):
    """Ideal half-bridge pole voltage: +Vdc/2 when reference > carrier, else -Vdc/2."""
    return np.where(ref > car, vdc / 2, -vdc / 2)

def gates(p):
    """Switch states (1 = on) from the pole voltage: (upper, lower). Ideal complementary pair, no dead time."""
    up = (p > 0).astype(float)
    return up, 1 - up

Load = namedtuple("Load", "f1 R L")  # series R-L load driven at fundamental frequency f1


#Dead time
def dead_samples(td_us, f1, n=N):
    """Dead time in grid samples (one sample is 1 / (f1 * n) seconds)."""
    return int(round(td_us * 1e-6 * f1 * n))


def dead_time_gates(cmd_up, dead):
    """Delay every turn-on by `dead` samples; turn-off is immediate. Returns (upper, lower) gate states."""
    late = np.roll(cmd_up, dead, axis=-1)
    return cmd_up * late, (1 - cmd_up) * (1 - late)


def pole_from_gates(up, lo, i_out, vdc):
    """Pole voltage. While both switches are off the load current picks the diode:
    i_out > 0 (current leaves the pole) flows through the lower diode, i_out < 0 through the upper one."""
    freewheel = np.where(i_out > 0, -vdc / 2, vdc / 2)
    return up * vdc / 2 - lo * vdc / 2 + (1 - up - lo) * freewheel


def _legs(cmd, dead, vdc, current_of=None, iters=6):
    """cmd: commanded upper-switch state per leg, shape (legs, N).
    current_of(poles) -> current leaving each pole. With dead time the pole voltage depends on that
    current and the current on the voltage, so a few fixed-point iterations settle it."""
    up, lo = dead_time_gates(cmd, dead) if dead else (cmd, 1 - cmd)
    P = (cmd - 0.5) * vdc  # ideal poles
    I = current_of(P) if current_of else None
    if dead and current_of:
        for _ in range(iters):
            P = pole_from_gates(up, lo, I, vdc)
            I = current_of(P)
    return up, lo, P, I

def _cmd(ref, car):
    """Commanded upper-switch state. A reference at or beyond the carrier range stays saturated, so a
    clamped phase (|ref| = 1) never gets a one-sample glitch where it touches the carrier peak."""
    hi, lo = ref >= 1 - 1e-12, ref <= -1 + 1e-12
    return np.where(hi, 1.0, np.where(lo, 0.0, (ref > car).astype(float)))

def _result(extra, up, lo, P, I):
    return {**extra, "gate_up": up, "gate_lo": lo, "poles": P, "i_legs": I,
            "i_load": None if I is None else I[0]}


#Topologies
def half_bridge(t, ma, mf, vdc, load=None, dead=0, kind="Triangle"):
    ref, car = sine(t, ma), carrier(t, mf, kind)
    cur = (lambda P: np.array([load_current(P[0], *load)])) if load else None
    up, lo, P, I = _legs(_cmd(ref, car)[None], dead, vdc, cur)
    return _result({"ref": ref, "car": car, "v_a0": P[0]}, up, lo, P, I)


def full_bridge(t, ma, mf, vdc, strategy="Unipolar", load=None, dead=0, kind="Triangle"):
    ref, car = sine(t, ma), carrier(t, mf, kind)
    cmd_a = _cmd(ref, car)
    if strategy == "Bipolar":  # leg B is the complement of leg A
        ref_b, cmd_b = None, 1 - cmd_a
    else:  # unipolar: leg B uses the inverted reference, same carrier
        ref_b = -ref
        cmd_b = _cmd(ref_b, car)     

    def cur(P):
        i = load_current(P[0] - P[1], *load)
        return np.array([i, -i])

    up, lo, P, I = _legs(np.array([cmd_a, cmd_b]), dead, vdc, cur if load else None)
    return _result({"ref": ref, "ref_b": ref_b, "car": car, "v_a0": P[0], "v_b0": P[1], "v_ab": P[0] - P[1]},
                   up, lo, P, I)


MODULATIONS = ["SPWM", "Third-harmonic injection", "SVPWM", "DPWM0", "DPWM1", "DPWM2",
               "DPWM-MAX", "DPWM-MIN", "Six-step"]
# Centre of the 60-degree clamp window relative to the peak of the phase voltage (positive = later).
DPWM_SHIFT = {"DPWM0": -np.pi / 6, "DPWM1": 0.0, "DPWM2": np.pi / 6}


def _dpwm(t, ma, mf, r, psi):
    """Discontinuous PWM: the phase with the largest |reference| of the frame shifted by psi is clamped to
    its rail (60 degrees per half cycle) and the same offset is added to all three phases.

    As in a digital controller the choice of the clamped phase is made once per carrier period (at its
    centre) and held. The offset still follows the reference, so the clamped phase stays exactly on its
    rail. Without this the jump of the offset would fall in the middle of a carrier period and bias the
    fundamental by several percent."""
    ts = (np.floor(t * mf) + 0.5) / mf
    shifted = np.array([sine(ts, ma, psi + k * 2 * np.pi / 3) for k in range(3)])
    k = np.argmax(np.abs(shifted), axis=0)[None]
    rail = np.sign(np.take_along_axis(shifted, k, 0))[0]
    return r + (rail - np.take_along_axis(r, k, 0)[0])


def three_phase_refs(t, ma, mod, mf=21):
    r = np.array([sine(t, ma, k * 2 * np.pi / 3) for k in range(3)])
    if mod == "SPWM":
        return r
    if mod.startswith("Third"):
        return r + ma * np.sin(6 * np.pi * t) / 6  # 1/6 of the 3rd harmonic
    if mod == "SVPWM":
        return r - (r.max(0) + r.min(0)) / 2  # min-max (zero-sequence) injection
    if mod in DPWM_SHIFT:
        return _dpwm(t, ma, mf, r, DPWM_SHIFT[mod])
    if mod == "DPWM-MAX":
        return r + (1 - r.max(0))  # highest phase clamped to +1
    if mod == "DPWM-MIN":
        return r - (1 + r.min(0))  # lowest phase clamped to -1
    if mod == "Six-step":  # 180-degree conduction: saturated references, m_a and the carrier play no role
        return np.array([np.sign(np.sin(2 * np.pi * t - k * 2 * np.pi / 3 + 1e-9)) for k in range(3)])
    raise ValueError(mod)


def three_phase(t, ma, mf, vdc, mod="SPWM", load=None, dead=0, kind="Triangle"):
    refs, car = three_phase_refs(t, ma, mod, mf), carrier(t, mf, kind)

    def cur(P):  # isolated neutral: each phase sees its pole minus the common-mode voltage
        return np.array([load_current(v, *load) for v in P - P.mean(0)])

    up, lo, P, I = _legs(_cmd(refs, car), dead, vdc, cur if load else None)
    vcm = P.mean(0)  # common-mode voltage of a balanced star load
    return _result({"refs": refs, "car": car, "v_ab": P[0] - P[1], "v_an": P[0] - vcm, "v_cm": vcm,
                    "v_abc": P - vcm},
                   up, lo, P, I)

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


#Switch losses
DEVICE = dict(vce0=1.0, rce=0.02, vf0=1.0, rd=0.015, eon=3e-3, eoff=2.5e-3, err=1.5e-3, vref=600.0, iref=50.0)


def leg_losses(pole_v, i_out, f1, vdc, dev=DEVICE):
    """Average losses [W] of one leg: {device: (conduction, switching)}.

    Transistor (V0 + r*i) and diode (V0 + r*i) conduction; switching energies scale linearly with
    current and DC voltage. i_out is the current leaving the pole. Conduction is decided by the pole
    voltage and the current sign, so dead-time freewheeling is handled automatically."""
    high, pos, ai = pole_v > 0, i_out > 0, np.abs(i_out)
    pT, pD = dev["vce0"] * ai + dev["rce"] * ai**2, dev["vf0"] * ai + dev["rd"] * ai**2
    cond = {"T_up": np.mean(np.where(high & pos, pT, 0)), "D_up": np.mean(np.where(high & ~pos, pD, 0)),
            "T_lo": np.mean(np.where(~high & ~pos, pT, 0)), "D_lo": np.mean(np.where(~high & pos, pD, 0))}
    nxt = np.roll(high, -1)
    rise, fall = ~high & nxt, high & ~nxt  # pole transitions
    k = f1 * ai * vdc / (dev["vref"] * dev["iref"])  # energy scaling, per event, times f1

    def sw(*terms):
        return float(sum(np.sum(np.where(m, e * k, 0)) for m, e in terms))

    switching = {"T_up": sw((rise & pos, dev["eon"]), (fall & pos, dev["eoff"])),
                 "D_up": sw((fall & ~pos, dev["err"])),
                 "T_lo": sw((fall & ~pos, dev["eon"]), (rise & ~pos, dev["eoff"])),
                 "D_lo": sw((rise & pos, dev["err"]))}
    return {d: (float(cond[d]), switching[d]) for d in cond}


#Clarke / Park
def clarke(x):
    """Amplitude-invariant Clarke transform of a three-phase set x (shape (3, N)): returns (alpha, beta)."""
    a, b, c = x
    return (2 * a - b - c) / 3, (b - c) / np.sqrt(3)


def park(alpha, beta, t):
    """Park transform. The d axis sits on the fundamental of phase A defined as sin(2 pi t), so a balanced
    set A*sin(...) gives d = A and q = 0 (a lagging current gives q < 0)."""
    th = 2 * np.pi * t - np.pi / 2
    return alpha * np.cos(th) + beta * np.sin(th), -alpha * np.sin(th) + beta * np.cos(th)


def carrier_average(x, mf):
    """Circular moving average over one carrier period: the 'averaged' vector the PWM tries to synthesise."""
    w = max(1, int(round(len(x) / mf)))
    k = np.zeros(len(x))
    k[:w] = 1 / w
    return np.real(np.fft.ifft(np.fft.fft(x) * np.fft.fft(np.roll(k, -(w // 2)))))