import streamlit as st

from pwmlab import core, metrics, plots, ui

st.set_page_config(page_title="Modulation comparison", layout="wide")
st.title("Modulation comparison")

topology = st.sidebar.radio("Topology", ["Three-phase", "Single-phase"])
three = topology == "Three-phase"
st.caption("Three-phase inverter. Every modulation runs with the same m_a, f_sw, carrier, load and dead time." if three
           else "Half bridge and full bridge. Every case runs with the same m_a, f_sw, load and dead time; the carrier "
                "(and for the full bridge the strategy) is part of the case.")
p = ui.sidebar_inputs(mf_default=39, ma_max=1.3, load_required=True, skip=() if three else ("carrier",))
if three:
    cases = st.sidebar.multiselect("Modulations", core.MODULATIONS,
                                   default=["SPWM", "SVPWM", "DPWM0", "DPWM1", "DPWM2", "Six-step"])
else:
    cases = st.sidebar.multiselect("Cases", metrics.SINGLE_PHASE_CASES,
                                   default=["Half bridge \u00b7 Triangle", "Full bridge \u00b7 Bipolar \u00b7 Triangle",
                                            "Full bridge \u00b7 Unipolar \u00b7 Triangle",
                                            "Full bridge \u00b7 Unipolar \u00b7 Sawtooth rising"])
dev, th = ui.device_inputs(), ui.thermal_inputs()


@st.cache_data(show_spinner=False)
def run(topology, cases, ma, mf, vdc, load, dead, kind, sampling, dev_items, th_items):
    return {c: metrics.case_metrics(topology, c, ma, mf, vdc, load, dead, kind, dict(dev_items), sampling,
                                    dict(th_items)) for c in cases}


if not cases:
    st.info("Pick at least one case in the sidebar.")
    st.stop()
res = run(topology, tuple(cases), p["ma"], p["mf"], p["vdc"], p["load"], p["dead"], p["carrier"], p["sampling"],
          tuple(sorted(dev.items())), tuple(sorted(th.items())))

HEADERS = {"v1": "v\u2081 [V]", "m_eff": "m_eff", "wthd": "WTHD [%]", "i_ripple": "I ripple [A]", "p_cond": "P cond [W]",
           "p_sw": "P sw [W]", "p_loss": "P loss [W]", "eff": "\u03b7 [%]", "vcm_rms": "v_cm rms [V]", "vcm_pk": "v_cm pk [V]",
           "h_dom": "Dominant harm. [f_sw]", "t_hs": "T heatsink [\u00b0C]", "tj_peak": "Tj peak [\u00b0C]",
           "tj_swing": "\u0394Tj [K]", "p_out": "P [W]", "q1": "Q\u2081 [var]", "s_app": "S [VA]", "pf": "PF",
           "dpf": "cos \u03c6\u2081", "dist": "S\u2081/S", "i_dist": "I\u2081/I_rms"}
PERFORMANCE = [("v1", 1), ("m_eff", 3), ("wthd", 2), ("i_ripple", 3), ("p_cond", 1), ("p_sw", 2), ("p_loss", 1),
               ("eff", 2)] + ([("vcm_rms", 1), ("vcm_pk", 1)] if three else [("h_dom", 2)])
THERMAL = [("t_hs", 1), ("tj_peak", 1), ("tj_swing", 1)]
POWER = [("p_out", 1), ("q1", 1), ("s_app", 1), ("pf", 3), ("dpf", 3), ("dist", 3), ("i_dist", 4)]


def table(columns):
    return [{"Modulation" if three else "Case": c, **{HEADERS[k]: round(res[c][k], nd) for k, nd in columns}}
            for c in cases]


st.dataframe(table(PERFORMANCE), hide_index=True)
st.caption("v\u2081: line-to-line (three-phase) or output (single-phase) fundamental, peak \u00b7 m_eff: effective modulation "
           "index \u00b7 WTHD of the output voltage \u00b7 \u03b7: efficiency of the switches only"
           + (" \u00b7 v_cm: common-mode voltage" if three else " \u00b7 dominant harm.: order of the strongest harmonic, in carrier frequencies"))
st.markdown("**Thermal**")
st.dataframe(table(THERMAL), hide_index=True)
st.caption("T heatsink: ambient + R_th,sa \u00b7 total loss. Tj peak: hottest junction. \u0394Tj: its swing over a fundamental period.")
st.markdown("**Output power quantities**")
st.dataframe(table(POWER), hide_index=True)
st.caption("P: active power (equals the output power) \u00b7 Q\u2081: fundamental reactive power \u00b7 S: apparent power \u00b7 "
           "PF = P/S \u00b7 cos \u03c6\u2081: displacement factor \u00b7 S\u2081/S: distortion factor (dominated by the PWM voltage) \u00b7 "
           "I\u2081/I_rms: distortion factor of the current")

available = [k for k in metrics.METRICS if k in res[cases[0]]]
key = st.selectbox("Chart", available, index=available.index("p_loss"),
                   format_func=lambda k: f"{metrics.METRICS[k][0]} [{metrics.METRICS[k][1]}]")
st.plotly_chart(plots.metric_bars(cases, [res[c][key] for c in cases], f"{metrics.METRICS[key][0]} [{metrics.METRICS[key][1]}]"))

with st.expander("How to read this"):
    for n in ([
        "m_eff is the line-to-line fundamental over the amplitude SPWM gives at m_a = 1, so it shows how much of the DC bus each modulation actually uses.",
        "Six-step ignores m_a and m_f: it always delivers its maximum voltage (m_eff = 4/\u03c0), so its losses are not comparable at 'equal m_a'. Look at its common-mode and ripple columns instead.",
        "DPWM trades higher WTHD and current ripple for fewer switching events. The gain depends on the load angle: compare DPWM0, DPWM1 and DPWM2 at different R and L.",
        "The common-mode voltage is practically the same for all carrier-based modulations here: DPWM does not reduce it, it reduces switching losses.",
        "Raise m_f to see switching losses grow, and the junction temperature with them. At low f_sw conduction dominates and every modulation has nearly the same efficiency.",
    ] if three else [
        "Half bridge and bipolar full bridge have the same spectrum shape and WTHD; the full bridge simply doubles the output voltage and the ripple. m_eff is normalised to V_dc/2 for the half bridge and to V_dc for the full bridge.",
        "Unipolar with a triangle carrier: the dominant harmonic moves to 2\u00b7f_sw, WTHD and current ripple fall sharply (about \u221270 % of ripple with the default settings), and the switching losses stay practically the same. The benefit is a smaller output filter, not efficiency.",
        "With a sawtooth carrier the unipolar advantage disappears: the dominant harmonic returns to f_sw and the ripple doubles.",
        "For the bipolar strategy and for the half bridge the carrier shape changes how the harmonics are distributed, not the WTHD or the ripple of a single leg.",
        "The full bridge has twice the devices and carries the full load current in each, so its heatsink and junctions run hotter than a single half bridge at the same settings.",
    ]):
        st.markdown(f"- {n}")