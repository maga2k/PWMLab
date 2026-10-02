"""Shared Streamlit widgets and result layout."""
import numpy as np
import streamlit as st

from . import core, plots


def sidebar_inputs(mf_default=15, ma_max=1.5):
    sb = st.sidebar
    p = {
        "ma": sb.slider("Modulation index  m\u2090", 0.0, ma_max, 0.8, 0.01,
                        help="Reference amplitude / carrier amplitude. Above 1 the converter overmodulates (above 1.155 for SVPWM/THI three-phase)."),
        "mf": sb.slider("Frequency ratio  m_f = f_sw / f\u2081", 3, 99, mf_default, 2,
                        help="Integer ratio: the pattern repeats every fundamental period, so the spectrum is exact. Odd values keep half-wave symmetry."),
        "vdc": sb.number_input("DC bus  V_dc [V]", 10.0, 2000.0, 400.0, 10.0),
        "f1": sb.number_input("Fundamental  f\u2081 [Hz]", 1.0, 1000.0, 50.0),
        "R": None, "L": None,
    }
    if sb.checkbox("Series R-L load", help="Adds the steady-state load current and its spectrum."):
        p["R"] = sb.number_input("R [\u03a9]", 0.01, 1000.0, 10.0)
        p["L"] = sb.number_input("L [mH]", 0.1, 1000.0, 20.0) / 1000
    return p


def add_load(p, v, label, rows, spectra):
    """Append load current (if enabled) to the plot rows and spectrum choices."""
    if p["R"]:
        i = core.load_current(v, p["f1"], p["R"], p["L"])
        rows.append(("Load current [A]", [(label, i)]))
        spectra["Load current"] = (i, "A")


def show(t, rows, spectra, p, notes):
    st.plotly_chart(plots.time_plot(t / p["f1"] * 1000, rows))
    st.subheader("Harmonic spectrum")
    c1, c2, c3 = st.columns([2, 2, 2])
    name = c1.selectbox("Signal", list(spectra))
    mode = c2.radio("Scale", ["Absolute", "% of fundamental"], horizontal=True)
    xmax = c3.slider("Max harmonic order", 10, 10 * p["mf"], 4 * p["mf"])
    x, unit = spectra[name]
    h, amp = core.spectrum(x)
    thd, wthd = core.distortion(h, amp)
    m1, m2, m3 = st.columns(3)
    m1.metric("Fundamental (peak)", f"{amp[1]:.2f} {unit}")
    m2.metric("THD", "n/a" if np.isnan(thd) else f"{thd * 100:.1f} %", help="Over all harmonics up to the Nyquist limit of the grid.")
    m3.metric("WTHD", "n/a" if np.isnan(wthd) else f"{wthd * 100:.2f} %", help="Harmonics weighted by 1/h: a better indicator of current ripple.")
    st.plotly_chart(plots.spectrum_plot(h, amp, xmax, unit, mode))
    with st.expander("What to look for"):
        for n in notes:
            st.markdown(f"- {n}")
