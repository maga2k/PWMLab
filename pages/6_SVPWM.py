import numpy as np
import streamlit as st

from pwmlab import core, plots

st.set_page_config(page_title="SVPWM", layout="wide")
st.title("Space-vector PWM")
st.caption("Sector, dwell times and switching sequence built explicitly. Triangle carrier, ideal switches, "
           "reference sampled once per carrier period.")

sb = st.sidebar
ma = sb.slider("Modulation index  m\u2090", 0.0, 1.3, 0.8, 0.01,
               help="Reference vector length over V_dc/2. The linear limit is 1.155 (vector length 1/\u221a3 \u00b7 V_dc).")
mf = sb.slider("Carrier periods per cycle  m_f", 6, 99, 24, 1)
vdc = sb.number_input("DC bus  V_dc [V]", 10.0, 2000.0, 400.0, 10.0)
f1 = sb.number_input("Fundamental  f\u2081 [Hz]", 1.0, 1000.0, 50.0)

t = core.time_grid()
sv = core.svpwm_explicit(t, ma, mf)
per = sv["period"]
k = st.slider("Carrier period to inspect", 0, mf - 1, 0)

ts = (np.floor(t * mf) + 0.5) / mf  # min-max injection with the reference sampled per carrier period
cmp = core._cmd(core.three_phase_refs(ts, ma, "SVPWM"), core.carrier(t, mf))
mismatch = int(np.sum((sv["gates"] != cmp).any(0)))

c = st.columns(5)
c[0].metric("Sector", int(per["sector"][k]))
c[1].metric("Angle in sector", f"{np.degrees(per['alpha'][k]):.1f}\u00b0")
c[2].metric("T1", f"{100 * per['t1'][k]:.1f} %")
c[3].metric("T2", f"{100 * per['t2'][k]:.1f} %")
c[4].metric("T0", f"{100 * per['t0'][k]:.1f} %")

tab_plane, tab_seq, tab_cycle = st.tabs(["Vector plane", "Switching sequence", "Over one cycle"])
with tab_plane:
    st.plotly_chart(plots.svpwm_plane(per, k, ma))
with tab_seq:
    widths = np.diff(np.concatenate([[0.0], per["cum"][k]]))
    st.dataframe([{"Segment": i + 1, "State (a b c)": "".join(map(str, per["states"][k][i])),
                   "Duration [% of T_s]": round(100 * w, 2)} for i, w in enumerate(widths)], hide_index=True)
    m = np.floor(t * mf).astype(int) == k
    x_ms = (t[m] * mf - k) * 1000 / (f1 * mf)
    gates = [(f"S_{leg}", sv["gates"][i][m]) for i, leg in enumerate("ABC")]
    st.plotly_chart(plots.time_plot(x_ms, [(f"Gate signals in carrier period {k}", gates, "digital")], step=1))
with tab_cycle:
    v_ab = (sv["gates"][0] - sv["gates"][1]) * vdc
    rows = [("Sector", [("sector", sv["sector"].astype(float))]),
            ("Dwell times (fraction of T_s)", [("T1", sv["t1"]), ("T2", sv["t2"]), ("T0", sv["t0"])]),
            ("Gate signals", [(f"S_{leg}", sv["gates"][i]) for i, leg in enumerate("ABC")], "digital"),
            ("Line-to-line v_AB [V]", [("v_AB", v_ab)])]
    st.plotly_chart(plots.time_plot(t / f1 * 1000, rows))
    st.metric("Line-to-line fundamental (peak)", f"{core.spectrum(v_ab)[1][1]:.1f} V",
              help=f"\u221a3/2 \u00b7 m_a \u00b7 V_dc = {np.sqrt(3) / 2 * ma * vdc:.1f} V in the linear range")

st.metric("Gates differing from min-max injection", f"{mismatch} of {t.size} samples",
          help="Min-max (centred zero vectors) injection compared against a triangle carrier, with the reference "
               "sampled at the centre of each carrier period. Identical in the linear range.")
with st.expander("What to look for"):
    for n in [
        "In the linear range the sequence 000 - Va - Vb - 111 - Vb - Va - 000 gives exactly the gates of min-max zero-sequence injection: SVPWM is that injection in disguise. The mismatch counter stays at 0.",
        "Odd sectors apply Vn then Vn+1, even sectors Vn+1 then Vn, so that only one leg switches at a time. Check the states in the sequence table.",
        "T0 is split equally between 000 and 111 (the symmetric choice). Changing that split gives the other zero-sequence schemes: all 111 clamps the highest phase (DPWM-MAX), all 000 the lowest (DPWM-MIN).",
        "At m_a = 1.155 the reference touches the hexagon: T0 reaches 0 mid-sector. Beyond it T1 and T2 are scaled down, which keeps the direction but flattens the amplitude.",
        "Each leg switches twice per carrier period, six commutations in total.",
    ]:
        st.markdown(f"- {n}")