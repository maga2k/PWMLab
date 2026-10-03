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
def run(mods, ma, mf, vdc, load, dead, kind, dev_items):
    return {m: metrics.three_phase_metrics(m, ma, mf, vdc, load, dead, kind, dict(dev_items)) for m in mods}


if not mods:
    st.info("Pick at least one modulation in the sidebar.")
    st.stop()
res = run(tuple(mods), p["ma"], p["mf"], p["vdc"], p["load"], p["dead"], p["carrier"], tuple(sorted(dev.items())))

COLUMNS = [("v1", 1), ("m_eff", 3), ("wthd", 2), ("i_ripple", 3), ("p_cond", 1), ("p_sw", 2), ("p_loss", 1),
           ("eff", 2), ("vcm_rms", 1), ("vcm_pk", 1)]
st.dataframe([{"Modulation": m, **{f"{metrics.METRICS[k][0]} [{metrics.METRICS[k][1]}]".replace(" []", ""):
                                    round(res[m][k], nd) for k, nd in COLUMNS}} for m in mods], hide_index=True)

key = st.selectbox("Chart", list(metrics.METRICS), index=list(metrics.METRICS).index("p_loss"),
                   format_func=lambda k: f"{metrics.METRICS[k][0]} [{metrics.METRICS[k][1]}]")
st.plotly_chart(plots.metric_bars(mods, [res[m][key] for m in mods], f"{metrics.METRICS[key][0]} [{metrics.METRICS[key][1]}]"))

with st.expander("How to read this"):
    for n in [
        "m_eff is the line-to-line fundamental over the amplitude SPWM gives at m_a = 1, so it shows how much of the DC bus each modulation actually uses.",
        "Six-step ignores m_a and m_f: it always delivers its maximum voltage (m_eff = 4/\u03c0), so its losses are not comparable at 'equal m_a'. Look at its common-mode and ripple columns instead.",
        "DPWM trades higher WTHD and current ripple for fewer switching events. The gain depends on the load angle: compare DPWM0, DPWM1 and DPWM2 at different R and L.",
        "The common-mode voltage is practically the same for all carrier-based modulations here: DPWM does not reduce it, it reduces switching losses.",
        "Raise m_f to see switching losses grow: at low f_sw conduction dominates and every modulation has nearly the same efficiency.",
    ]:
        st.markdown(f"- {n}")