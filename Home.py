import streamlit as st

st.set_page_config(page_title="PWMLab", layout="wide")
st.title("PWMLab")
st.markdown(
    "An interactive tool to explore carrier-based PWM in power electronics. "
    "Pick a topology in the sidebar, move the sliders, and watch the carrier, "
    "the output voltage, its harmonic spectrum and the load current follow."
)
st.info("Switches are ideal and the DC bus is stiff. This is not a circuit simulator: "
        "play with it, notice something odd, then work out why.")

st.page_link("pages/1_Half_Bridge.py", label="Half bridge", icon="1\ufe0f\u20e3")
st.page_link("pages/2_Full_Bridge.py", label="Full bridge: bipolar vs unipolar", icon="2\ufe0f\u20e3")
st.page_link("pages/3_Three_Phase.py", label="Three-phase inverter: SPWM, THI, SVPWM, DPWM", icon="3\ufe0f\u20e3")
st.page_link("pages/4_Modulation_Comparison.py", label="Modulation comparison", icon="4\ufe0f\u20e3")
st.page_link("pages/5_Sweeps.py", label="Sweeps: f_sw and m_a", icon="5\ufe0f\u20e3")
st.page_link("pages/6_SVPWM.py", label="Space-vector PWM, step by step", icon="6\ufe0f\u20e3")

st.subheader("How it computes")
st.markdown(
    "- Switching instants come from comparing reference and carrier on a fine grid (2^15 samples per fundamental period).\n"
    "- Spectra are FFTs over exactly one fundamental period (integer m_f), so there is no leakage.\n"
    "- Load current is the periodic steady state of a series R-L load: I_h = V_h / Z_h.\n"
    "- `tests/` checks the results against closed-form values (e.g. textbook Bessel-function harmonics)."
)
