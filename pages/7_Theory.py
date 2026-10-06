import numpy as np
import plotly.graph_objects as go
import streamlit as st

from pwmlab import core, schematics as sch, theory, ui

st.set_page_config(page_title="Theory", layout="wide")
st.title("Theory")
st.caption("The formulas behind the simulations. Where it makes sense, the numbers on the other pages are checked "
           "against them in the test suite.")

tab_pwm, tab_vec, tab_loss = st.tabs(["PWM and spectra", "Three-phase and space vectors", "Load, losses and thermal"])

# ----------------------------------------------------------------------------------------------------------------
with tab_pwm:
    st.subheader("From reference to pole voltage")
    ui.show_svg(sch.modulator())
    st.markdown("A carrier-based modulator compares a reference with a carrier. The comparator output drives the "
                "two switches of a leg (complementary, with a dead time). The leg then imposes one of two voltages "
                "on its **pole**, referred to the middle point of the DC bus.")
    left, right = st.columns(2)
    with left:
        ui.show_svg(sch.half_bridge())
    with right:
        ui.show_svg(sch.full_bridge())
    st.latex(r"m_a=\frac{\hat v_{ref}}{\hat v_{carrier}},\qquad m_f=\frac{f_{sw}}{f_1},\qquad "
             r"v_{A0}=\begin{cases}+V_{dc}/2 & v_{ref}>v_{carrier}\\ -V_{dc}/2 & \text{otherwise}\end{cases}")
    st.markdown("In the linear range ($m_a\\le 1$) the average of the pole voltage over a carrier period follows the "
                "reference, so the fundamental is proportional to $m_a$:")
    st.latex(r"\hat V_1=m_a\,\frac{V_{dc}}{2}\ \ \text{(half bridge)},\qquad \hat V_1=m_a\,V_{dc}\ \ \text{(full bridge)}")

    st.subheader("Harmonics of a triangle carrier")
    st.markdown("With a triangle carrier and natural sampling the spectrum has no baseband harmonics: everything sits "
                "in groups around the multiples of $f_{sw}$. The component at order $m\\,m_f+n$ (in multiples of "
                "$f_1$) has the peak amplitude")
    st.latex(r"A_{m,n}=\frac{2V_{dc}}{m\pi}\,\left|J_n\!\left(m\,\frac{\pi m_a}{2}\right)\right|"
             r"\quad\text{for } m+n \text{ odd, and } 0 \text{ otherwise}")
    st.markdown("where $J_n$ is the Bessel function of the first kind. So the first group is the carrier itself "
                "($m=1,n=0$) with sidebands at $f_{sw}\\pm2f_1,\\ \\pm4f_1,\\dots$ and no component at $f_{sw}\\pm f_1$. "
                "A **sawtooth** carrier modulates one edge only: every sideband order appears "
                "($f_{sw}\\pm f_1,\\ \\pm2f_1,\\dots$) and so does a component at $2f_{sw}$.")
    with st.expander("Check the formula against the simulation", expanded=True):
        c1, c2 = st.columns(2)
        ma = c1.slider("Modulation index m_a", 0.1, 1.0, 0.8, 0.05, key="th_ma")
        mf = c2.slider("Frequency ratio m_f", 9, 99, 21, 2, key="th_mf")
        vdc = 400.0
        formula = theory.triangle_harmonics(ma, mf, vdc, m_max=2, n_max=6)
        sim = core.spectrum(core.half_bridge(core.time_grid(), ma, mf, vdc)["v_a0"])[1]
        orders = sorted(h for h in formula if h > 1)
        fig = go.Figure()
        fig.add_bar(x=orders, y=[sim[h] for h in orders], name="simulation (FFT)")
        fig.add_scatter(x=orders, y=[formula[h] for h in orders], mode="markers", name="formula",
                        marker=dict(symbol="diamond", size=9, color="#e45756"))
        fig.update_layout(height=320, margin=dict(t=10, b=10, l=10, r=10), xaxis_title="Harmonic order (multiples of f\u2081)",
                          yaxis_title="Amplitude [V]", legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
        st.plotly_chart(fig)
        st.caption(f"Fundamental: formula {formula[1]:.2f} V, simulation {sim[1]:.2f} V. The diamonds fall on the bars; "
                   "the orders in between are exactly zero in both.")

    st.subheader("Bipolar and unipolar full bridge")
    st.latex(r"v_{AB}=v_{A0}-v_{B0}")
    st.markdown("- **Bipolar**: leg B is the complement of leg A, so $v_{AB}=2v_{A0}$ and the output switches between "
                "$\\pm V_{dc}$. The spectrum is the half-bridge one, doubled.\n"
                "- **Unipolar**: leg B uses the inverted reference with the same carrier. The terms with odd $m$ cancel in "
                "$v_{AB}$, so the first group is centred on $2f_{sw}$ and the output has three levels "
                "($+V_{dc},0,-V_{dc}$): the load sees a bridge that switches at twice the frequency, with the same "
                "switching losses per leg. With a sawtooth carrier the cancellation is lost.")

    st.subheader("Regular sampling")
    st.markdown("A digital modulator reads the reference once per carrier period (symmetric) or twice (asymmetric) "
                "and holds it. This delays the output and, for a low $m_f$, adds baseband distortion:")
    st.latex(r"\text{symmetric: }\ \Delta t=\frac{T_c}{2},\ \varphi=\frac{\pi}{m_f},\ |H|\approx\operatorname{sinc}\frac{1}{m_f}"
             r"\qquad\text{asymmetric: }\ \Delta t=\frac{T_c}{4},\ |H|\approx\operatorname{sinc}\frac{1}{2m_f}")
    st.markdown("with $\\operatorname{sinc}x=\\sin(\\pi x)/(\\pi x)$. At $m_f=15$ the symmetric mode produces about "
                "0.9 % of baseband distortion; the asymmetric one brings it back to 0.05 %, like the natural case.")

# ----------------------------------------------------------------------------------------------------------------
with tab_vec:
    st.subheader("Three legs, one common point")
    left, right = st.columns([3, 2])
    with left:
        ui.show_svg(sch.three_phase())
    with right:
        st.markdown("With an isolated neutral each phase sees its pole minus the **common-mode voltage**:")
        st.latex(r"v_{kN}=v_{k0}-v_{cm}")
        st.latex(r"v_{cm}=\frac{v_{a0}+v_{b0}+v_{c0}}{3}")
        st.latex(r"v_{ab}=v_{a0}-v_{b0}")
        st.markdown("$v_{cm}$ can only take the values $\\pm V_{dc}/2$ (states 000 and 111) and $\\pm V_{dc}/6$: its "
                    "peak is $V_{dc}/2$ whatever carrier-based modulation is used. Triplen harmonics are common "
                    "mode, so they cancel in $v_{ab}$ and $v_{kN}$.")
    st.subheader("Switching states and space vectors")
    left, right = st.columns(2)
    with left:
        ui.show_svg(sch.hexagon())
    with right:
        st.markdown("The eight switch states give seven distinct vectors: six **active** vectors of length "
                    "$2V_{dc}/3$ and two **zero** vectors.")
        st.markdown("| State (a b c) | Vector | Angle | $v_{an},v_{bn},v_{cn}$ in units of $V_{dc}/3$ |\n|---|---|---|---|\n"
                    "| 000, 111 | V0, V7 | \u2013 | 0, 0, 0 |\n| 100 | V1 | 0\u00b0 | 2, \u22121, \u22121 |\n"
                    "| 110 | V2 | 60\u00b0 | 1, 1, \u22122 |\n| 010 | V3 | 120\u00b0 | \u22121, 2, \u22121 |\n"
                    "| 011 | V4 | 180\u00b0 | \u22122, 1, 1 |\n| 001 | V5 | 240\u00b0 | \u22121, \u22121, 2 |\n"
                    "| 101 | V6 | 300\u00b0 | 1, \u22122, 1 |")
        st.markdown("Amplitude-invariant **Clarke** and **Park** transforms (the d axis sits on the fundamental "
                    "of phase A):")
        st.latex(r"v_\alpha=\frac{2v_a-v_b-v_c}{3},\quad v_\beta=\frac{v_b-v_c}{\sqrt3},\quad "
                 r"\begin{pmatrix}v_d\\ v_q\end{pmatrix}=\begin{pmatrix}\cos\theta&\sin\theta\\ -\sin\theta&\cos\theta\end{pmatrix}"
                 r"\begin{pmatrix}v_\alpha\\ v_\beta\end{pmatrix}")
        st.markdown("The reference vector has length $m_aV_{dc}/2$. It can be synthesised on average only inside the "
                    "hexagon; the largest circle that fits is the **linear range**:")
        st.latex(r"|\vec v_{ref}|\le\frac{V_{dc}}{\sqrt3}\ \Rightarrow\ m_a\le\frac{2}{\sqrt3}\approx1.155,\qquad "
                 r"\hat V_{LL}=\sqrt3\,m_a\frac{V_{dc}}{2}")
    st.subheader("Space-vector PWM")
    st.markdown("In a carrier period $T_s$ the reference in sector $n$ (angle $\\alpha$ from vector $V_n$) is built "
                "from the two adjacent active vectors and the zero vectors:")
    st.latex(r"\frac{T_1}{T_s}=\sqrt3\,\frac{|\vec v_{ref}|}{V_{dc}}\sin\!\left(\frac{\pi}{3}-\alpha\right),\quad "
             r"\frac{T_2}{T_s}=\sqrt3\,\frac{|\vec v_{ref}|}{V_{dc}}\sin\alpha,\quad T_0=T_s-T_1-T_2")
    st.markdown("The symmetric sequence $000\\to V_n\\to V_{n+1}\\to111\\to V_{n+1}\\to V_n\\to000$ splits $T_0$ equally "
                "between the two zero vectors (odd and even sectors swap $V_n$ and $V_{n+1}$ so that one leg switches "
                "at a time). That is **exactly** a carrier modulation with a zero-sequence offset added to the three "
                "references (the SVPWM page checks it sample by sample):")
    st.markdown("| Modulation | Zero-sequence offset $v_0$ (references normalised to the carrier) | Linear up to |\n|---|---|---|\n"
                "| SPWM | 0 | $m_a=1$ |\n| Third-harmonic injection | $\\frac{m_a}{6}\\sin3\\omega t$ | 1.155 |\n"
                "| SVPWM | $-\\frac{\\max+\\min}{2}$ (T0 split equally) | 1.155 |\n"
                "| DPWM-MAX / MIN | $1-\\max$ / $-1-\\min$ (all T0 on 111 / 000) | 1.155 |\n"
                "| DPWM0 / 1 / 2 | clamp the phase with the largest $\\lvert ref\\rvert$ of the frame shifted by \u221230\u00b0 / 0\u00b0 / +30\u00b0 | 1.155 |")
    st.markdown("The clamped phase does not switch for 60\u00b0 per half cycle (120\u00b0 for MAX/MIN), which removes a third "
                "of the switching events. Clarke removes any common offset, so all of them trace the same circle in the "
                "$\\alpha\\beta$ plane.")
    st.subheader("Six-step")
    st.latex(r"\hat V_{an,1}=\frac{2}{\pi}V_{dc},\quad \hat V_{ab,1}=\frac{2\sqrt3}{\pi}V_{dc},\quad "
             r"\frac{\hat V_h}{\hat V_1}=\frac1h\ (h=6k\pm1),\quad THD_{an}=\sqrt{\frac{\pi^2}{9}-1}\approx31\,\%")
    st.markdown("This is the largest voltage the bridge can give: $m_{eff}=4/\\pi\\approx1.273$ relative to SPWM at "
                "$m_a=1$, and a common-mode voltage of only $\\pm V_{dc}/6$.")
    ui.page_link("pages/6_SVPWM.py", "See the sector, dwell times and sequence of a carrier period", "\u27a1\ufe0f")

# ----------------------------------------------------------------------------------------------------------------
with tab_loss:
    st.subheader("Series R-L load")
    st.markdown("In periodic steady state each harmonic of the voltage drives its own current component:")
    st.latex(r"I_h=\frac{V_h}{R+jh\omega_1L},\qquad \varphi_1=\arctan\frac{\omega_1L}{R}")
    st.markdown("The load filters the carrier harmonics: the current ripple falls as $1/f_{sw}$. Output quantities, with "
                "$v(t)$ the voltage across the load (summed over the phases):")
    st.latex(r"P=\frac1T\!\int v\,i\,dt=R\,I_{rms}^2,\quad S=V_{rms}I_{rms},\quad Q_1=\tfrac12\hat V_1\hat I_1\sin\varphi_1,"
             r"\quad D^2=S^2-P^2-Q_1^2")
    st.latex(r"PF=\frac{P}{S},\qquad \text{displacement factor}=\cos\varphi_1,\qquad "
             r"\text{current distortion factor}=\frac{I_1}{I_{rms}}")
    st.markdown("At the output of a PWM inverter $S$ is dominated by the voltage harmonics, which carry almost no "
                "active power: $PF$ is low even when the current is clean. The displacement factor and the "
                "current distortion factor describe what the load actually sees.")

    st.subheader("Dead time")
    st.markdown("Every turn-on is delayed by $t_d$. While both switches are off the load current chooses the diode, so "
                "the pole voltage follows its sign: it is $-V_{dc}/2$ if the current leaves the pole and $+V_{dc}/2$ "
                "otherwise. Averaged over a carrier period each leg loses")
    st.latex(r"\Delta v=-V_{dc}\,t_d\,f_{sw}\,\operatorname{sign}(i),\qquad "
             r"\hat{\Delta V}_1=\frac{4}{\pi}V_{dc}\,t_d\,f_{sw}")
    st.markdown("an error that is a square wave in phase with the current. It lowers the fundamental by about "
                "$\\hat{\\Delta V}_1\\cos\\varphi_1$ and, in a three-phase inverter, adds the 5th, 7th, 11th, 13th\u2026 "
                "harmonics with amplitude proportional to $1/h$.")

    st.subheader("Switch losses")
    left, right = st.columns(2)
    with left:
        st.markdown("**Conduction.** The pole voltage and the current sign tell which device carries the current:")
        st.markdown("| Pole | Current $i$ | Device |\n|---|---|---|\n| high | > 0 | T_up |\n| high | < 0 | D_up |\n"
                    "| low | < 0 | T_lo |\n| low | > 0 | D_lo |")
        st.latex(r"p_T=(V_{ce0}+r_{ce}|i|)\,|i|,\qquad p_D=(V_{f0}+r_d|i|)\,|i|")
    with right:
        st.markdown("**Switching.** Every pole transition costs energy, scaled from the test point:")
        st.markdown("| Pole | Current $i$ | Event |\n|---|---|---|\n| rises | > 0 | T_up on, D_lo recovery |\n"
                    "| rises | < 0 | T_lo off |\n| falls | > 0 | T_up off |\n| falls | < 0 | T_lo on, D_up recovery |")
        st.latex(r"E=E_{ref}\,\frac{|i|}{I_{ref}}\,\frac{V_{dc}}{V_{ref}},\qquad P_{sw}=f_1\sum_{events}E")
    st.markdown("Switching energy is proportional to $|i|$ at the instant of the transition. This is why a "
                "discontinuous modulation works best when its clamp window is centred on the **current** peak, not on "
                "the voltage peak: with an R-L load the current lags, so DPWM2 wins.")

    st.subheader("Thermal model")
    left, right = st.columns([3, 2])
    with left:
        ui.show_svg(sch.thermal_network())
    with right:
        st.markdown("All devices share one heatsink, whose time constant is far longer than a fundamental period, so "
                    "it follows the mean total loss. Each junction adds its own $R_{jc}$ through a first-order thermal "
                    "impedance, solved harmonic by harmonic like the load current.")
    st.latex(r"T_{hs}=T_{amb}+R_{sa}\sum P,\qquad Z_{th}(\omega)=\frac{R_{jc}}{1+j\omega\tau}")
    st.latex(r"T_j(t)=T_{hs}+\sum_h\operatorname{Re}\left\{Z_{th}(h\omega_1)\,P_h\,e^{jh\omega_1t}\right\}")
    st.markdown("A power component of amplitude $\\hat P$ at frequency $f$ swings the junction by "
                "$\\Delta T=2\\hat P\\,R_{jc}/\\sqrt{1+(2\\pi f\\tau)^2}$: the lower the output frequency, the larger the swing.")
    tau = st.slider("Junction time constant \u03c4 [ms]", 1, 50, 10, key="th_tau_theory") / 1000
    f = np.logspace(0, 3, 200)
    fig = go.Figure(go.Scatter(x=f, y=theory.thermal_attenuation(f, tau), mode="lines", showlegend=False))
    marks = [5, 50, 400]
    fig.add_scatter(x=marks, y=[float(theory.thermal_attenuation(m, tau)) for m in marks], mode="markers+text",
                    text=[f"{m} Hz: {float(theory.thermal_attenuation(m, tau)):.2f}" for m in marks],
                    textposition="top right", marker=dict(size=9, color="#e45756"), showlegend=False)
    fig.update_layout(height=300, margin=dict(t=30, b=10, l=10, r=10), xaxis_type="log", xaxis_dtick=1,
                      xaxis_title="Frequency of the power component [Hz]", yaxis_title="|Z_th| / R_jc")
    st.plotly_chart(fig)
    st.caption("This model resolves the swing at the fundamental frequency and its harmonics, not the switching ripple.")