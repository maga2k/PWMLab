"""Shared Streamlit widgets and result layout."""
import numpy as np
import streamlit as st
from .plots import losses_plot

from . import core, metrics, plots


def sidebar_inputs(mf_default=15, ma_max=1.5, load_required=False, skip=()):
    """Common sidebar. load_required: no checkbox, the R-L load is always on. skip: names ("ma", "mf") of
    inputs to hide because the page sweeps them."""
    sb = st.sidebar
    p = {"carrier": sb.selectbox("Carrier", core.CARRIERS,
                                help="Triangle: both edges move (double-edge). Sawtooth: one edge is fixed at the start of each carrier period, only the other moves (single-edge)."),
         "sampling": sb.selectbox("Reference sampling", core.SAMPLING,
                                  help="Natural: the reference is compared continuously (analog). Symmetric: read once per carrier period, at the carrier peak. Asymmetric: read twice per period, at peak and trough. Regular sampling delays the output by 1/2 (symmetric) or 1/4 (asymmetric) of a carrier period."),
         "ma": 0.8, "mf": mf_default}
    if "ma" not in skip:
        p["ma"] = sb.slider("Modulation index  m\u2090", 0.0, ma_max, 0.8, 0.01,
                            help="Reference amplitude / carrier amplitude. Above 1 the converter overmodulates (above 1.155 for SVPWM/THI three-phase).")
    if "mf" not in skip:
        p["mf"] = sb.slider("Frequency ratio  m_f = f_sw / f\u2081", 3, 99, mf_default, 2,
                            help="Integer ratio: the pattern repeats every fundamental period, so the spectrum is exact. Odd values keep half-wave symmetry.")
    p["vdc"] = sb.number_input("DC bus  V_dc [V]", 10.0, 2000.0, 400.0, 10.0)
    p["f1"] = sb.number_input("Fundamental  f\u2081 [Hz]", 1.0, 1000.0, 50.0)
    p["load"], p["dead"] = None, 0
    if load_required or sb.checkbox("Series R-L load", help="Adds the steady-state load current. Needed for dead time and losses."):
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

def device_inputs():
    """Device parameters (shared with the Losses tab through the widget keys)."""
    dev = dict(core.DEVICE)
    with st.expander("Device parameters (transistor + antiparallel diode)"):
        cols = st.columns(3)
        for k, (key, label, scale, step) in enumerate(FIELDS):
            dev[key] = cols[k % 3].number_input(label, min_value=0.001, value=float(core.DEVICE[key] * scale),
                                                step=float(step), key=f"dev_{key}") / scale
    return dev

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
    st.plotly_chart(
        losses_plot(leg),
        use_container_width=True,
    )

def clarke_park_tab(p, s):
    """Space vector in the alpha-beta plane and its d/q components (three-phase only)."""
    kinds = ["Phase voltage"] + (["Load current"] if s["i_legs"] is not None else [])
    volt = st.radio("Vector", kinds, horizontal=True) == "Phase voltage"
    x, unit = (s["v_abc"], "V") if volt else (s["i_legs"], "A")
    t = core.time_grid()
    alpha, beta = core.clarke(x)
    d, q = core.park(alpha, beta, t)
    avg = lambda y: core.carrier_average(y, p["mf"])
    ref = tuple(p["vdc"] / 2 * z for z in core.clarke(s["refs"])) if volt else None
    left, right = st.columns(2)
    left.plotly_chart(plots.vector_plot(alpha, beta, avg(alpha), avg(beta), ref, p["vdc"] if volt else None, unit))
    rows = [(f"d axis [{unit}]", [("instantaneous", d), ("carrier average", avg(d))]),
            (f"q axis [{unit}]", [("instantaneous", q), ("carrier average", avg(q))])]
    right.plotly_chart(plots.time_plot(t / p["f1"] * 1000, rows))
    m1, m2, m3 = st.columns(3)
    m1.metric("d (mean)", f"{d.mean():.2f} {unit}")
    m2.metric("q (mean)", f"{q.mean():.2f} {unit}")
    m3.metric("|dq| (mean)", f"{np.hypot(d.mean(), q.mean()):.2f} {unit}")
    st.caption("Amplitude-invariant Clarke. The d axis sits on the fundamental of phase A, so a balanced set "
               "gives constant d and q = 0; a lagging current has q < 0.")


def power_tab(p, s, v_key, n_phases=1):
    """Output power quantities of the R-L load. v_key: load voltage in the result dict (n_phases rows)."""
    if s["i_legs"] is None:
        st.info("Enable the series R-L load in the sidebar: the power quantities need the load current.")
        return
    v, i = np.atleast_2d(s[v_key]), s["i_legs"][:n_phases]
    q = metrics.power_quantities(v, i)
    c = st.columns(4)
    c[0].metric("Active power P", f"{q['p']:.1f} W")
    c[1].metric("Reactive power Q\u2081", f"{q['q1']:.1f} var", help="Fundamental only; positive for an inductive load.")
    c[2].metric("Apparent power S", f"{q['s']:.1f} VA", help="Sum over the phases of V_rms \u00b7 I_rms.")
    c[3].metric("Distortion power D", f"{q['d']:.1f} VA", help="S\u00b2 = P\u00b2 + Q\u2081\u00b2 + D\u00b2")
    c = st.columns(4)
    c[0].metric("Power factor P/S", f"{q['pf']:.3f}")
    c[1].metric("Displacement factor cos \u03c6\u2081", f"{q['dpf']:.3f}", help="Phase shift between the fundamentals of voltage and current.")
    c[2].metric("Distortion factor S\u2081/S", f"{q['dist']:.3f}", help="Share of the apparent power carried by the fundamentals. PF is close to the product of the two factors.")
    c[3].metric("Current distortion factor I\u2081/I_rms", f"{q['i_dist']:.4f}", help="Distortion of the load current alone.")
    st.caption("At the inverter output the voltage is the PWM waveform, so S\u2081/S and the power factor are low even when "
               "the current is clean: the harmonics of the voltage show up as distortion power D. The displacement factor "
               "and the current distortion factor are what the load sees.")
    left, right = st.columns(2)
    left.plotly_chart(plots.metric_bars(["P", "Q\u2081", "D", "S"], [q["p"], q["q1"], q["d"], q["s"]], "W / var / VA"))
    inst = np.sum(v * i, axis=0)
    right.plotly_chart(plots.time_plot(core.time_grid() / p["f1"] * 1000,
                                       [("Instantaneous power [W]", [("p(t)", inst), ("P (mean)", np.full_like(inst, q["p"]))])]))  

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
