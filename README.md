# PWMLab

An interactive Streamlit app to explore carrier-based PWM in power electronics: half bridge,
full bridge and three-phase inverter, with gate signals, dead time, harmonic spectra, switch
losses and Clarke/Park analysis. Move a slider and the carrier, gate signals, output voltages,
spectrum, load current and losses follow.

It is not a circuit simulator: switches are ideal, the DC bus is stiff and the load is a linear
series R-L. The goal is to see how a modulation scheme behaves and why, not to replace a
detailed simulation.

## What is in it

Every page shares the same controls: carrier (triangle, rising sawtooth, falling sawtooth),
modulation index m_a, frequency ratio m_f = f_sw / f_1, DC bus, fundamental frequency, an optional
series R-L load and, with the load enabled, the dead time.

| Page | Topology | What you can compare |
|---|---|---|
| Half bridge | One leg, pole voltage at +/- V_dc/2 | Spectrum with triangle vs sawtooth, effect of dead time |
| Full bridge | Two legs | Bipolar vs unipolar PWM, with a triangle or a sawtooth carrier |
| Three-phase | Three legs, star load, isolated neutral | SPWM, third-harmonic injection, SVPWM, DPWM0/1/2, DPWM-MAX/MIN, six-step |

Each page has tabs:

- **Waveforms**: reference and carrier, gate signals of every switch, pole, line, phase and
  common-mode voltages, load current.
- **Spectrum**: harmonic spectrum of any signal, absolute or as % of the fundamental, with THD and
  WTHD (harmonics weighted by 1/h).
- **Losses** (needs the load): conduction and switching losses of transistor and diode of one leg,
  loss breakdown chart, output power and efficiency of the switches. Device parameters are editable.
- **Clarke / Park** (three-phase): space vector in the alpha-beta plane with the hexagon and the
  linear-range circle, instantaneous vector vs carrier-averaged vector, d and q components of the
  phase voltage or of the load current.

## Three-phase modulations

| Modulation | Zero-sequence term |
|---|---|
| SPWM | None, pure sines. Linear up to m_a = 1 |
| Third-harmonic injection | 1/6 of the third harmonic. Linear up to m_a = 1.155 |
| SVPWM | Min-max injection (centred zero vectors). Linear up to m_a = 1.155 |
| DPWM0 / DPWM1 / DPWM2 | One phase clamped to a rail for 60 degrees per half cycle. The window is centred -30 / 0 / +30 degrees from the peak of the phase voltage |
| DPWM-MAX / DPWM-MIN | One phase clamped for 120 degrees on a single rail (upper / lower) |
| Six-step | Square-wave operation, 180 degree conduction. m_a, m_f and the carrier are ignored |

The best DPWM window follows the current peak, not the voltage peak: with a current lagging by about
30 degrees (the default R-L load) DPWM2 gives the lowest switching losses. DPWM0 would suit a leading
current, which an R-L load cannot produce. The DPWM naming is not uniform in the literature, so the
convention above is the one used here.

## Models and conventions

- Ideal switches and a stiff DC bus. All voltages are referred to the DC midpoint, so a pole voltage is
  +V_dc/2 or -V_dc/2.
- m_a is the peak of the reference over the carrier amplitude, i.e. the peak phase voltage over V_dc/2.
  m_f must be an integer, so the pattern repeats every fundamental period.
- Everything is computed on a grid of 2^15 samples per fundamental period. Spectra are FFTs over exactly
  one period, so there is no leakage.
- The load is a series R-L in periodic steady state, solved harmonic by harmonic (I_h = V_h / Z_h).
  The three-phase load is a balanced star with isolated neutral.
- Dead time delays every turn-on and leaves turn-off immediate. While both switches are off the load
  current picks the diode: current leaving the pole flows through the lower diode, current entering it
  through the upper one. Voltage and current depend on each other, so the pole voltage is found by a few
  fixed-point iterations. The grid resolution is 1 / (f_1 * 2^15), and the effective dead time is shown
  in the sidebar.
- DPWM0/1/2 take the clamp decision once per carrier period and hold it, as a digital controller does.
  Near the window edges an unclamped reference can therefore exceed +/-1 slightly: the modulator
  saturates it and the fundamental is unaffected.
- Losses: transistor and diode conduction as V_0 + r*i, switching energies (E_on, E_off, diode E_rr)
  scaled linearly with current and DC voltage from the test point, applied at every pole transition.
  One leg is computed and scaled by the number of legs, assuming symmetry. Efficiency counts the
  switches only.
- Clarke is amplitude-invariant. The Park d axis sits on the fundamental of phase A, so a balanced set
  gives constant d and q = 0, and a lagging current has q < 0.

## Run it locally

```bash
python -m venv .venv
# Windows:     .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run Home.py
```

Open the folder in VS Code, select the `.venv` interpreter, and run the command in the integrated
terminal.

## Tests

```bash
pytest
```

The tests compare the results with closed-form or textbook values rather than with themselves:

- fundamental amplitudes and linear modulation limits for every topology and modulation
- the bipolar full-bridge carrier harmonic (a Bessel-function value), harmonic cancellation in the
  line-to-line voltage, loss of frequency doubling in the unipolar bridge with a sawtooth
- carrier shapes and the edge locked to the carrier period in sawtooth modulation
- six-step: fundamental 2*sqrt(3)/pi * V_dc, harmonics 1/h, phase-voltage THD of 31 %
- dead time: no gate overlap, gap duration, self-consistency with the current, and the fundamental
  against an analytic phasor estimate
- loss identities (conduction losses add up to r*i^2, switching losses scale with V_dc), DPWM
  switching less than SPWM, best clamp window for a lagging current
- Clarke/Park of a balanced set, invisibility of the zero-sequence term in alpha-beta, sign of q for a
  lagging current

## Project layout

```
Home.py            landing page
pages/             one file per topology (Streamlit builds the sidebar navigation from this folder)
pwmlab/core.py     all the maths: pure NumPy, no Streamlit
pwmlab/plots.py    Plotly figures
pwmlab/ui.py       sidebar widgets, tabs and result layout
tests/             pytest suite
```

## Roadmap

- Modulation comparison: same m_a, f_sw and load, one table with WTHD, RMS current ripple, switching and
  conduction losses, efficiency and common-mode voltage for each modulation
- Sweeps over f_sw and m_a (losses, ripple, WTHD, efficiency), and fundamental vs m_a from the linear
  range to six-step
- Explicit space-vector SVPWM: sector, dwell times T1/T2/T0 and switching sequence, checked against the
  min-max injection
- Regular sampling (symmetric / asymmetric)
- Thermal model: junction temperature from R_jc per device and a shared heatsink resistance
- Datasheet-based device data: switching energy curves instead of linear scaling
- Output power quantities: P, Q, S, displacement and distortion factor
- Exact Fourier series instead of the FFT
- R-L load with back-EMF
- Cross-check of selected cases against ngspice (via PySpice)

## License

MIT