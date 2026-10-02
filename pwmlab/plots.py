import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def time_plot(t_ms, rows, step=4):
    """rows = [(title, [(trace_name, y), ...]), ...]; all rows share one time axis."""
    fig = make_subplots(rows=len(rows), cols=1, shared_xaxes=True, vertical_spacing=0.07,
                        subplot_titles=[r[0] for r in rows])
    for i, (_, traces) in enumerate(rows, 1):
        for name, y in traces:
            fig.add_scatter(x=t_ms[::step], y=y[::step], name=name, mode="lines", row=i, col=1)
    fig.update_xaxes(title_text="Time [ms]", row=len(rows), col=1)
    fig.update_layout(height=230 * len(rows), margin=dict(t=40, b=10, l=10, r=10), legend=dict(orientation="h"))
    return fig


def spectrum_plot(h, amp, xmax, unit, mode):
    pct = mode.startswith("%") and amp[1] > 1e-9
    y = amp / amp[1] * 100 if pct else amp
    mask = (h >= 1) & (h <= xmax)
    keep = mask & (y > 1e-4 * y[mask].max())
    fig = go.Figure(go.Bar(x=h[keep], y=y[keep], width=0.6))
    fig.update_layout(height=320, margin=dict(t=10, b=10, l=10, r=10),
                      xaxis_title="Harmonic order (multiples of f\u2081)",
                      yaxis_title="% of fundamental" if pct else f"Amplitude [{unit}]")
    return fig
