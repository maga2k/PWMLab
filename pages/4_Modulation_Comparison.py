import streamlit as st

from pwmlab import core, metrics, plots, ui

st.set_page_config(page_title="Modulation comparison", layout="wide")
st.title("Modulation comparison")
st.caption("Three-phase inverter. Every modulation runs with the same m_a, f_sw, carrier, load and dead time.")

p = ui.sidebar_inputs(mf_default=39, ma_max=1.3, load_required=True)
mods = st.sidebar.multiselect("Modulations", core.MODULATIONS,
                              default=["SPWM", "SVPWM", "DPWM0", "DPWM1", "DPWM2", "Six-step"])
dev = ui.device_inputs()


@st.cache_data(show_spinner=False)
def run(mods, ma, mf, vdc, load, dead, kind, sampling, dev_items):
    return {m: metrics.three_phase_metrics(m, ma, mf, vdc, load, dead, kind, dict(dev_items), sampling) for m in mods}


if not mods:
    st.info("Pick at least one modulation in the sidebar.")
    st.stop()
res = run(tuple(mods), p["ma"], p["mf"], p["vdc"], p["load"], p["dead"], p["carrier"], p["sampling"],
          tuple(sorted(dev.items())))

HEADERS = {"v1": "v\u2081 [V]", "m_eff": "m_eff", "wthd": "WTHD [%]", "i_ripple": "I ripple [A]", "p_cond": "P cond [W]",
           "p_sw": "P sw [W]", "p_loss": "P loss [W]", "eff": "\u03b7 [%]", "vcm_rms": "v_cm rms [V]", "vcm_pk": "v_cm pk [V]",
           "p_out": "P [W]", "q1": "Q\u2081 [var]", "s_app": "S [VA]", "pf": "PF", "dpf": "cos \u03c6\u2081", "dist": "S\u2081/S",
           "i_dist": "I\u2081/I_rms"}
PERFORMANCE = [("v1", 1), ("m_eff", 3), ("wthd", 2), ("i_ripple", 3), ("p_cond", 1), ("p_sw", 2), ("p_loss", 1),
               ("eff", 2), ("vcm_rms", 1), ("vcm_pk", 1)]
POWER = [("p_out", 1), ("q1", 1), ("s_app", 1), ("pf", 3), ("dpf", 3), ("dist", 3), ("i_dist", 4)]


def table(columns):
    return [{"Modulation": m, **{HEADERS[k]: round(res[m][k], nd) for k, nd in columns}} for m in mods]


st.dataframe(table(PERFORMANCE), hide_index=True)
st.caption("v\u2081: line-to-line fundamental (peak) \u00b7 m_eff: effective modulation index \u00b7 WTHD of v_AB \u00b7 "
           "\u03b7: efficiency of the switches only \u00b7 v_cm: common-mode voltage")
st.markdown("**Output power quantities**")
st.dataframe(table(POWER), hide_index=True)
st.caption("P: active power (equals the output power) \u00b7 Q\u2081: fundamental reactive power \u00b7 S: apparent power \u00b7 "
           "PF = P/S \u00b7 cos \u03c6\u2081: displacement factor \u00b7 S\u2081/S: distortion factor (dominated by the PWM voltage) \u00b7 "
           "I\u2081/I_rms: distortion factor of the current")
with st.expander("How to read this"):
    for n in [
        "m_eff is the line-to-line fundamental over the amplitude SPWM gives at m_a = 1, so it shows how much of the DC bus each modulation actually uses.",
        "Six-step ignores m_a and m_f: it always delivers its maximum voltage (m_eff = 4/\u03c0), so its losses are not comparable at 'equal m_a'. Look at its common-mode and ripple columns instead.",
        "DPWM trades higher WTHD and current ripple for fewer switching events. The gain depends on the load angle: compare DPWM0, DPWM1 and DPWM2 at different R and L.",
        "The common-mode voltage is practically the same for all carrier-based modulations here: DPWM does not reduce it, it reduces switching losses.",
        "Raise m_f to see switching losses grow: at low f_sw conduction dominates and every modulation has nearly the same efficiency.",
    ]:
        st.markdown(f"- {n}")