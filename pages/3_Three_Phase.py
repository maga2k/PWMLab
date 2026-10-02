import streamlit as st

from pwmlab import core, ui

st.set_page_config(page_title="Three-phase", layout="wide")
st.title("Three-phase inverter")
st.caption("Three legs, star load with isolated neutral, shared carrier.")

mod = st.sidebar.selectbox("Modulation", core.MODULATIONS,
                           help="SPWM: pure sines. THI/SVPWM: add a zero-sequence term (linear up to 1.155). "
                                "DPWM0/1/2: one phase is clamped to a rail for 60\u00b0 per half cycle, window centred -30\u00b0/0\u00b0/+30\u00b0 from the phase voltage peak. "
                                "DPWM-MAX/MIN: 120\u00b0 on a single rail. Six-step: square-wave operation.")
if mod == "Six-step":
    st.sidebar.info("Six-step ignores m\u2090, m_f and the carrier.")
p = ui.sidebar_inputs(ma_max=1.3)
t = core.time_grid()
s = core.three_phase(t, p["ma"], p["mf"], p["vdc"], mod, p["load"], p["dead"], p["carrier"])

gate_traces = [(f"S_{k}{sign}", g[i]) for i, k in enumerate("ABC") for sign, g in (("+", s["gate_up"]), ("\u2212", s["gate_lo"]))]
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
    "Line-to-line fundamental in the linear range is \u221a3/2 \u00b7 m\u2090 \u00b7 V_dc for every modulation except six-step.",
    "SPWM saturates at m\u2090 = 1; THI, SVPWM and all DPWM stay linear up to m\u2090 = 1.155 (about 15 % more voltage). Compare at m\u2090 = 1.1.",
    "Triplen harmonics (3, 9, ...) are common-mode: they cancel in v_AB when m_f is a multiple of 3.",
    "The harmonic at f_sw is pure common-mode too: select 'Common-mode v_N0' and compare it with v_AB.",
    "DPWM clamps every phase to a rail for 120\u00b0 per cycle (the flat segments in the pole voltage). DPWM0/1/2 move the 60\u00b0 windows by -30\u00b0/0\u00b0/+30\u00b0 relative to the phase voltage peak; DPWM-MAX/MIN put 120\u00b0 on one rail.",
    "Enable the load and open Losses: the best clamp window follows the current peak, not the voltage. With the default load (about 32\u00b0 lag) DPWM2 beats DPWM1 and DPWM0. DPWM0 suits a leading current, which an R-L load cannot produce.",
    "Sawtooth carrier: the locked edge of all three legs falls on the same instant, line-to-line harmonics near f_sw grow and WTHD is roughly 50 % higher than with a triangle.",
    "Six-step: line-to-line fundamental is 2\u221a3/\u03c0 \u00b7 V_dc (about 1.10 V_dc), harmonics only at 6k\u00b11 with amplitude 1/h of the fundamental, phase-voltage THD about 31 %.",
    "Clarke / Park tab: zero-sequence injection (THI, SVPWM, DPWM) is invisible in \u03b1\u03b2, so the averaged vector is the same circle for all of them; what changes is which vectors build it. Six-step sits on the hexagon vertices. In dq the fundamental is a DC value and the PWM harmonics become ripple.",
    "Losses tab: DPWM switches each leg for only 2/3 of the period, so switching losses drop compared with SPWM at the same f_sw.",
], extras={"Losses": lambda: ui.losses_tab(p, s, n_legs=3, n_phases=3),
           "Clarke / Park": lambda: ui.clarke_park_tab(p, s)})