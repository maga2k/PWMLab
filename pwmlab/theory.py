"""Closed-form results shown on the Theory page, kept here so the tests can compare them with the simulation."""
import numpy as np

_trapz = getattr(np, "trapezoid", None) or np.trapz


def bessel_j(n, x):
    """Bessel function of the first kind, integer order n, from its integral representation."""
    tau = np.linspace(0.0, np.pi, 2001)
    return float(_trapz(np.cos(n * tau - x * np.sin(tau)), tau) / np.pi)


def triangle_harmonics(ma, mf, vdc, m_max=3, n_max=6):
    """Half bridge, triangle carrier, natural sampling: peak amplitude of the pole voltage harmonics.

    Returns {order (multiples of f1): amplitude}. Baseband: m_a V_dc / 2 at order 1. Carrier groups sit at
    m * m_f + n with amplitude (2 V_dc / (m pi)) |J_n(m pi m_a / 2)|, and only for m + n odd."""
    out = {1: ma * vdc / 2}
    for m in range(1, m_max + 1):
        for n in range(-n_max, n_max + 1):
            if (m + n) % 2 and m * mf + n > 0:
                out[m * mf + n] = 2 * vdc / (m * np.pi) * abs(bessel_j(n, m * np.pi * ma / 2))
    return out


def dead_time_fundamental(vdc, td, fsw):
    """Fundamental of the dead-time error of one leg: a square wave of amplitude V_dc * t_d * f_sw, in phase
    with the sign of the load current."""
    return 4 / np.pi * vdc * td * fsw


def thermal_attenuation(f, tau):
    """|Z_th| / R_jc of a first-order junction at frequency f: how much of a power component survives."""
    return 1 / np.sqrt(1 + (2 * np.pi * np.asarray(f) * tau) ** 2)