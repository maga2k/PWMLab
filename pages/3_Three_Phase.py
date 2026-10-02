import streamlit as st

from pwmlab import core, ui

st.set_page_config(page_title="Three-phase", layout="wide")
st.title("Three-phase inverter")
st.caption("Three legs, star load with isolated neutral, shared triangular carrier.")

mod = st.sidebar.selectbox("Modulation", core.MODULATIONS,
                           help="SPWM: pure sines. THI/SVPWM: add a zero-sequence term (extends linear range to 1.155). DPWM: one phase is clamped to a rail for 120\u00b0 (fewer switchings).")
p = ui.sidebar_inputs(ma_max=1.3)
t = core.time_grid()
s = core.three_phase(t, p["ma"], p["mf"], p["vdc"], mod, p["load"], p["dead"])

gate_traces = [(f"S_{k}{sign}", g[i]) for i, k in enumerate("ABC")
               for sign, g in (("+", s["gate_up"]), ("\u2212", s["gate_lo"]))]
rows = [("References and carrier (p.u.)",
         [(f"ref {k}", s["refs"][i]) for i, k in enumerate("ABC")] + [("carrier", s["car"])]),
        ("Gate signals", gate_traces, "digital"),
        ("Pole voltage v_A0 [V]", [("v_A0", s["poles"][0])]),
        ("Line-to-line v_AB [V]", [("v_AB", s["v_ab"])]),
        ("Phase voltage v_AN [V]", [("v_AN", s["v_an"])]),
        ("Common-mode voltage v_N0 [V]", [("v_N0", s["v_cm"])])]
spectra = {"Line-to-line v_AB": (s["v_ab"], "V"), "Phase voltage v_AN": (s["v_an"], "V"),
           "Pole voltage v_A0": (s["poles"][0], "V"), "Common-mode v_N0": (s["v_cm"], "V")}
ui.add_load(p, s["i_load"], "i_A", rows, spectra)

ui.show(t, rows, spectra, p, [
    "Line-to-line fundamental in the linear range is \u221a3/2 \u00b7 m\u2090 \u00b7 V_dc for every modulation shown.",
    "SPWM saturates at m\u2090 = 1; THI and SVPWM stay linear up to m\u2090 = 1.155 (about 15 % more voltage). Compare at m\u2090 = 1.1.",
    "Triplen harmonics (3, 9, ...) are common-mode: they cancel in v_AB when m_f is a multiple of 3.",
    "The harmonic at f_sw is pure common-mode too: select 'Common-mode v_N0' and compare it with v_AB.",
    "DPWM modulations clamp a phase for 120\u00b0: watch the flat segments in the pole voltage.",
    "Losses tab: DPWM switches each leg for only 2/3 of the period, so switching losses drop compared with SPWM at the same f_sw.",
], extras={"Losses": lambda: ui.losses_tab(p, s, n_legs=3, n_phases=3)})