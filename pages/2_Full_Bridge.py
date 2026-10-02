import streamlit as st

from pwmlab import core, ui

st.set_page_config(page_title="Full bridge", layout="wide")
st.title("Full-bridge PWM")
st.caption("Two legs. Bipolar: output switches between \u00b1V_dc. Unipolar: output has three levels (+V_dc, 0, \u2212V_dc).")

strategy = st.sidebar.radio("Strategy", ["Unipolar", "Bipolar"],
                            help="Bipolar: leg B is the complement of leg A. Unipolar: leg B uses the inverted reference.")
p = ui.sidebar_inputs()
t = core.time_grid()
s = core.full_bridge(t, p["ma"], p["mf"], p["vdc"], strategy)

ref_traces = [("reference", s["ref"]), ("carrier", s["car"])]
if s["ref_b"] is not None:
    ref_traces.insert(1, ("\u2212reference", s["ref_b"]))
rows = [("Reference and carrier (p.u.)", ref_traces),
        ("Pole voltages [V]", [("v_A0", s["v_a0"]), ("v_B0", s["v_b0"])]),
        ("Output voltage v_AB [V]", [("v_AB", s["v_ab"])])]
spectra = {"Output voltage v_AB": (s["v_ab"], "V")}
ui.add_load(p, s["v_ab"], "i_load", rows, spectra)

ui.show(t, rows, spectra, p, [
    "Both strategies give a fundamental of m\u2090\u00b7V_dc in the linear range.",
    "Bipolar: strong harmonic at f_sw (about 0.82\u00b7V_dc at m\u2090 = 0.8). Unipolar: nothing at f_sw, the first group is at 2f_sw.",
    "With a load, unipolar has far less current ripple at the same switching frequency: the output effectively switches at 2f_sw with half the voltage step.",
    "Try m_f = 15 and compare both strategies on the spectrum of the load current.",
])
