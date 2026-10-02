import streamlit as st

from pwmlab import core, ui

st.set_page_config(page_title="Half bridge", layout="wide")
st.title("Half-bridge PWM")
st.caption("One inverter leg, triangular carrier. Output is referred to the DC midpoint (\u00b1V_dc/2).")

p = ui.sidebar_inputs()
t = core.time_grid()
s = core.half_bridge(t, p["ma"], p["mf"], p["vdc"], p["load"], p["dead"], p["carrier"])

rows = [("Reference and carrier (p.u.)", [("reference", s["ref"]), ("carrier", s["car"])]),
        ("Gate signals", [("S_A+", s["gate_up"][0]), ("S_A\u2212", s["gate_lo"][0])], "digital"),
        ("Pole voltage v_A0 [V]", [("v_A0", s["v_a0"])])]
spectra = {"Pole voltage v_A0": (s["v_a0"], "V")}
ui.add_load(p, s["i_load"], "i_load", rows, spectra)

ui.show(t, rows, spectra, p, [
    "In the linear range (m\u2090 \u2264 1) the fundamental is m\u2090\u00b7V_dc/2, independent of the switching frequency.",
    "Triangle carrier: the first harmonic group sits at f_sw, with sidebands at f_sw \u00b1 2f\u2081, f_sw \u00b1 4f\u2081... only.",
    "Sawtooth carrier: only one edge moves, the other is locked to the carrier period (trailing edge for rising, leading edge for falling). Every sideband order appears (f_sw \u00b1 f\u2081, \u00b1 2f\u2081...) plus a strong component at 2f_sw. WTHD barely changes for a single leg.",
    "Push m\u2090 above 1: low-order harmonics appear (overmodulation).",
    "Switch the load on and raise m_f: voltage THD barely moves, but the current ripple shrinks.",
    "Add dead time: both gates are low for a moment after each command edge, and the pole voltage in the gap follows the sign of the current.",
    "Dead time lowers the fundamental, more so at high f_sw and when the current is in phase with the voltage. THD and low-order harmonics grow.",
], extras={"Losses": lambda: ui.losses_tab(p, s)})