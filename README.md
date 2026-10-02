# PWMLab

An interactive Streamlit app to explore carrier-based PWM in power electronics: half bridge,
full bridge (bipolar / unipolar) and three-phase inverter (SPWM, third-harmonic injection,
SVPWM, DPWM). Move the sliders and the carrier, gate-level output voltages, harmonic spectrum,
THD/WTHD and load current follow.

It is not a circuit simulator: switches are ideal, the DC bus is stiff, the load is a linear series R-L.

## Run it locally

```bash
python -m venv .venv
# Windows:    .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run Home.py
```

Open the folder in VS Code, select the `.venv` interpreter, and run the command in the integrated terminal.

## Tests

```bash
pytest
```

The tests compare the results with closed-form values (fundamental amplitudes, linear modulation
limits, textbook Bessel-function harmonic of the bipolar full bridge, harmonic cancellation, R-L limits).

## Project layout

```
Home.py            landing page
pages/             one file per topology (Streamlit builds the sidebar navigation from this folder)
pwmlab/core.py     all the maths: pure NumPy, no Streamlit
pwmlab/plots.py    Plotly figures
pwmlab/ui.py       shared sidebar widgets and result layout
tests/             pytest suite
```

## Roadmap

- Regular sampling (symmetric / asymmetric) and sawtooth carriers
- Dead time with diode conduction and zero-current clamping
- Space-vector hexagon with the averaged voltage vector
- Exact Fourier series instead of the FFT
- R-L load with back-EMF

## License

MIT
