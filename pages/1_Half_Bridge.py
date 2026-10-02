import streamlit as st

from pwmlab import core, ui

st.set_page_config(page_title="Half bridge", layout="wide")
st.title("Half-bridge PWM")
st.caption("One inverter leg, triangular carrier. Output is referred to the DC midpoint (\u00b1V_dc/2).")

p = ui.sidebar_inputs()
t = core.time_grid()
s = core.half_bridge(t, p["ma"], p["mf"], p["vdc"])
up, lo = core.gates(s["v_a0"])

rows = [("Reference and carrier (p.u.)", [("reference", s["ref"]), ("carrier", s["car"])]),
        ("Gate signals", [("S_A+", up), ("S_A\u2212", lo)], "digital"),
        ("Pole voltage v_A0 [V]", [("v_A0", s["v_a0"])])]

spectra = {"Pole voltage v_A0": (s["v_a0"], "V")}
ui.add_load(p, s["v_a0"], "i_load", rows, spectra)

ui.show(t, rows, spectra, p, [
    "In the linear range (m\u2090 \u2264 1) the fundamental is m\u2090\u00b7V_dc/2, independent of the switching frequency.",
    "The first harmonic group sits at f_sw, with sidebands at f_sw \u00b1 2f\u2081, f_sw \u00b1 4f\u2081...",
    "Push m\u2090 above 1: low-order harmonics appear (overmodulation).",
    "Switch the load on and raise m_f: voltage THD barely moves, but the current ripple shrinks.",
])
