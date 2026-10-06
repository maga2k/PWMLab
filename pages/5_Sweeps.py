import numpy as np
import streamlit as st

from pwmlab import core, metrics, plots, ui

st.set_page_config(page_title="Sweeps", layout="wide")
st.title("Sweeps")

topology = st.sidebar.radio("Topology", ["Three-phase", "Single-phase"])
three = topology == "Three-phase"
st.caption("One parameter varies, the rest is fixed in the sidebar." + ("" if three else " The carrier (and for the full bridge the strategy) is part of the case."))
what = st.sidebar.radio("Sweep", ["Switching frequency", "Modulation index"])
swept = "mf" if what == "Switching frequency" else "ma"
p = ui.sidebar_inputs(mf_default=39, ma_max=1.3, load_required=True, skip=(swept,) + (() if three else ("carrier",)))
if three:
    cases = st.sidebar.multiselect("Modulations", core.MODULATIONS, default=["SPWM", "SVPWM", "DPWM1", "DPWM2"])
else:
    cases = st.sidebar.multiselect("Cases", metrics.SINGLE_PHASE_CASES,
                                   default=["Half bridge \u00b7 Triangle", "Full bridge \u00b7 Bipolar \u00b7 Triangle",
                                            "Full bridge \u00b7 Unipolar \u00b7 Triangle"])
n = st.sidebar.slider("Points", 4, 25, 10)
if swept == "mf":
    lo, hi = st.sidebar.slider("m_f range", 5, 399, (9, 399))
    values = sorted({int(2 * round((v - 1) / 2) + 1) for v in np.linspace(lo, hi, n)})  # odd integers
    x, xlabel = np.array(values) * p["f1"] / 1000, "Switching frequency [kHz]"
    fixed = {"ma": p["ma"]}
else:
    lo, hi = st.sidebar.slider("m_a range", 0.05, 2.0, (0.1, 1.5))
    values = [float(v) for v in np.round(np.linspace(lo, hi, n), 4)]
    x, xlabel = np.array(values), "Modulation index m_a"
    fixed = {"mf": p["mf"]}
fixed.update(vdc=p["vdc"], load=p["load"], dead=p["dead"], kind=p["carrier"], sampling=p["sampling"])
dev, th = ui.device_inputs(), ui.thermal_inputs()


@st.cache_data(show_spinner="Running the sweep...")
def run(topology, swept, values, cases, fixed, dev_items, th_items):
    return {c: metrics.case_sweep(topology, c, swept, values, dev=dict(dev_items), thermal=dict(th_items), **dict(fixed))
            for c in cases}


if not cases:
    st.info("Pick at least one case in the sidebar.")
    st.stop()
res = run(topology, swept, tuple(values), tuple(cases), tuple(sorted(fixed.items())), tuple(sorted(dev.items())),
          tuple(sorted(th.items())))

available = [k for k in metrics.METRICS if k in res[cases[0]]]
default = (["wthd", "i_ripple", "p_sw", "eff", "tj_peak"] if swept == "mf"
           else ["m_eff", "wthd", "eff", "vcm_rms" if three else "tj_peak"])
keys = st.multiselect("Metrics", available, default=default,
                      format_func=lambda k: f"{metrics.METRICS[k][0]} [{metrics.METRICS[k][1]}]")
cols = st.columns(2)
for i, key in enumerate(keys):
    label, unit = metrics.METRICS[key]
    cols[i % 2].plotly_chart(plots.sweep_plot(x, {c: res[c][key] for c in cases}, xlabel, f"{label} [{unit}]"))

with st.expander("What to look for"):
    for n_ in ([
        "Switching losses grow linearly with f_sw, while current ripple falls as 1/f_sw: the sweep shows where the extra losses stop paying off.",
        "The peak junction temperature follows the losses, so the penalty of a high f_sw shows up as a thermal limit, not only as lost efficiency.",
        "WTHD of the output voltage does not depend much on f_sw; the current ripple does, because the load filters the carrier harmonics.",
        "To reach 20 kHz with f\u2081 = 50 Hz you need m_f = 400: use the range slider. The grid has 32768 samples per period, so very high m_f gets coarse.",
    ] + ([
        "DPWM keeps its switching-loss advantage at every f_sw, but only the right clamp window (DPWM2 for the default lagging load) gets the full benefit.",
    ] if three else [
        "Unipolar with a triangle carrier reaches the ripple of a bipolar bridge at a much lower f_sw: at equal ripple it switches less and loses less.",
    ]) if swept == "mf" else [
        "m_eff follows m_a up to 1 (single-phase: until the reference touches the carrier) and up to 1.155 for SVPWM, THI and DPWM in the three-phase case, then bends towards the square-wave limit.",
        "Beyond the linear range low-order harmonics appear: watch WTHD rise as the output moves towards a square wave.",
        "Efficiency can improve at high m_a only because the output power grows faster than the losses.",
    ]):
        st.markdown(f"- {n_}")