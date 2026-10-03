import numpy as np
import streamlit as st

from pwmlab import core, metrics, plots, ui

st.set_page_config(page_title="Sweeps", layout="wide")
st.title("Sweeps")
st.caption("Three-phase inverter. One parameter varies, the rest is fixed in the sidebar.")

what = st.sidebar.radio("Sweep", ["Switching frequency", "Modulation index"])
swept = "mf" if what == "Switching frequency" else "ma"
p = ui.sidebar_inputs(mf_default=39, ma_max=1.3, load_required=True, skip=(swept,))
mods = st.sidebar.multiselect("Modulations", core.MODULATIONS, default=["SPWM", "SVPWM", "DPWM1", "DPWM2"])
n = st.sidebar.slider("Points", 4, 25, 10)
if swept == "mf":
    lo, hi = st.sidebar.slider("m_f range", 5, 399, (9, 99))
    values = sorted({int(2 * round((v - 1) / 2) + 1) for v in np.linspace(lo, hi, n)})  # odd integers
    x, xlabel = np.array(values) * p["f1"] / 1000, "Switching frequency [kHz]"
    fixed = {"ma": p["ma"]}
else:
    lo, hi = st.sidebar.slider("m_a range", 0.05, 2.0, (0.1, 1.5))
    values = [float(v) for v in np.round(np.linspace(lo, hi, n), 4)]
    x, xlabel = np.array(values), "Modulation index m_a"
    fixed = {"mf": p["mf"]}
fixed.update(vdc=p["vdc"], load=p["load"], dead=p["dead"], kind=p["carrier"])
dev = ui.device_inputs()


@st.cache_data(show_spinner="Running the sweep...")
def run(swept, values, mods, fixed, dev_items):
    return {m: metrics.sweep(swept, values, mod=m, dev=dict(dev_items), **dict(fixed)) for m in mods}


if not mods:
    st.info("Pick at least one modulation in the sidebar.")
    st.stop()
res = run(swept, tuple(values), tuple(mods), tuple(sorted(fixed.items())), tuple(sorted(dev.items())))

default = ["wthd", "i_ripple", "p_sw", "eff"] if swept == "mf" else ["m_eff", "wthd", "eff", "vcm_rms"]
keys = st.multiselect("Metrics", list(metrics.METRICS), default=default,
                      format_func=lambda k: f"{metrics.METRICS[k][0]} [{metrics.METRICS[k][1]}]")
cols = st.columns(2)
for i, key in enumerate(keys):
    label, unit = metrics.METRICS[key]
    cols[i % 2].plotly_chart(plots.sweep_plot(x, {m: res[m][key] for m in mods}, xlabel, f"{label} [{unit}]"))

with st.expander("What to look for"):
    for n_ in ([
        "Switching losses grow linearly with f_sw, while current ripple falls as 1/f_sw: the sweep shows where the extra losses stop paying off.",
        "DPWM keeps its switching-loss advantage at every f_sw, but only the right clamp window (DPWM2 for the default lagging load) gets the full benefit.",
        "WTHD of the line voltage does not depend much on f_sw; the current ripple does, because the load filters the carrier harmonics.",
        "To reach 20 kHz with f\u2081 = 50 Hz you need m_f = 400: use the range slider. The grid has 32768 samples per period, so very high m_f gets coarse.",
    ] if swept == "mf" else [
        "m_eff follows m_a up to 1 for SPWM and up to 1.155 for SVPWM, THI and DPWM, then bends towards 4/\u03c0 (six-step) as m_a grows.",
        "Beyond the linear range low-order harmonics appear: watch WTHD rise as the output moves towards a square wave.",
        "Six-step ignores m_a, so it is a flat reference line.",
        "Efficiency can improve at high m_a only because the output power grows faster than the losses.",
    ]):
        st.markdown(f"- {n_}")