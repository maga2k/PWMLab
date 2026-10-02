"""Shared Streamlit widgets and result layout."""
import numpy as np
import streamlit as st

from . import core, plots


def sidebar_inputs(mf_default=15, ma_max=1.5):
    sb = st.sidebar
    p = {
        "carrier": sb.selectbox("Carrier", core.CARRIERS,
                                help="Triangle: both edges move (double-edge). Sawtooth: one edge is fixed at the start of each carrier period, only the other moves (single-edge)."),
        "ma": sb.slider("Modulation index  m\u2090", 0.0, ma_max, 0.8, 0.01,
                        help="Reference amplitude / carrier amplitude. Above 1 the converter overmodulates (above 1.155 for SVPWM/THI three-phase)."),
        "mf": sb.slider("Frequency ratio  m_f = f_sw / f\u2081", 3, 99, mf_default, 2,
                        help="Integer ratio: the pattern repeats every fundamental period, so the spectrum is exact. Odd values keep half-wave symmetry."),
        "vdc": sb.number_input("DC bus  V_dc [V]", 10.0, 2000.0, 400.0, 10.0),
        "f1": sb.number_input("Fundamental  f\u2081 [Hz]", 1.0, 1000.0, 50.0),
        "load": None, "dead": 0,
    }
    if sb.checkbox("Series R-L load", help="Adds the steady-state load current. Needed for dead time and losses."):
        R = sb.number_input("R [\u03a9]", 0.01, 1000.0, 10.0)
        L = sb.number_input("L [mH]", 0.1, 1000.0, 20.0) / 1000
        p["load"] = core.Load(p["f1"], R, L)
        td = sb.slider("Dead time [\u00b5s]", 0.0, 10.0, 0.0, 0.5,
                       help="Delay applied to every turn-on. The pole voltage during the gap follows the current direction.")
        p["dead"] = core.dead_samples(td, p["f1"])
        if td:
            us = 1e6 / (p["f1"] * core.N)
            sb.caption(f"Grid resolution {us:.2f} \u00b5s, effective dead time {p['dead'] * us:.2f} \u00b5s.")
    return p


def add_load(p, i, label, rows, spectra):
    """Append the load current (None when the load is off) to the plot rows and spectrum choices."""
    if i is not None:
        rows.append(("Load current [A]", [(label, i)]))
        spectra["Load current"] = (i, "A")


FIELDS = [("vce0", "Transistor V\u2080 [V]", 1, 0.1), ("rce", "Transistor r [m\u03a9]", 1e3, 1.0),
          ("vf0", "Diode V\u2080 [V]", 1, 0.1), ("rd", "Diode r [m\u03a9]", 1e3, 1.0),
          ("eon", "E_on [mJ]", 1e3, 0.1), ("eoff", "E_off [mJ]", 1e3, 0.1), ("err", "E_rr [mJ]", 1e3, 0.1),
          ("vref", "Test voltage [V]", 1, 10.0), ("iref", "Test current [A]", 1, 5.0)]


def losses_tab(p, s, n_legs=1, n_phases=1):
    """Loss breakdown of one leg, scaled to n_legs; efficiency of the converter stage only."""
    if p["load"] is None:
        st.info("Enable the series R-L load in the sidebar: losses depend on the load current.")
        return
    dev = dict(core.DEVICE)
    with st.expander("Device parameters (transistor + antiparallel diode)"):
        cols = st.columns(3)
        for k, (key, label, scale, step) in enumerate(FIELDS):
            dev[key] = cols[k % 3].number_input(label, min_value=0.001, value=float(core.DEVICE[key] * scale),
                                                step=float(step), key=f"dev_{key}") / scale
        st.caption("Switching energies are given at the test voltage/current and scaled linearly with V_dc and current.")
    leg = core.leg_losses(s["poles"][0], s["i_legs"][0], p["f1"], p["vdc"], dev)
    p_loss = n_legs * sum(c + w for c, w in leg.values())
    p_out = n_phases * p["load"].R * np.mean(s["i_legs"][0] ** 2)
    m1, m2, m3 = st.columns(3)
    m1.metric("Output power", f"{p_out:.1f} W")
    m2.metric(f"Switch losses ({n_legs} leg{'s' if n_legs > 1 else ''})", f"{p_loss:.1f} W")
    m3.metric("Efficiency (switches only)", f"{100 * p_out / (p_out + p_loss):.2f} %" if p_out > 0 else "n/a")
    st.dataframe([{"Device (one leg)": d, "Conduction [W]": round(c, 3), "Switching [W]": round(w, 3),
                   "Total [W]": round(c + w, 3)} for d, (c, w) in leg.items()], hide_index=True)


def show(t, rows, spectra, p, notes, extras=None):
    """extras: {tab name: zero-argument callable that draws the tab}."""
    extras = extras or {}
    tabs = st.tabs(["Waveforms", "Spectrum"] + list(extras))
    with tabs[0]:
        st.plotly_chart(plots.time_plot(t / p["f1"] * 1000, rows))
    with tabs[1]:
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
    for tab, draw in zip(tabs[2:], extras.values()):
        with tab:
            draw()
    with st.expander("What to look for"):
        for n in notes:
            st.markdown(f"- {n}")
