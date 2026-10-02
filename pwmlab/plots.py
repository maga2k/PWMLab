import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def time_plot(t_ms, rows, step=4):
    """rows = [(title, [(name, y), ...]) or (title, [...], "digital"), ...]; all rows share one time axis.

    A "digital" row stacks its 0/1 traces vertically and labels the y axis with the signal names."""
    digital = [len(r) > 2 and r[2] == "digital" for r in rows]
    weights = [1 + 0.3 * len(r[1]) if d else 1 for r, d in zip(rows, digital)]
    fig = make_subplots(rows=len(rows), cols=1, shared_xaxes=True, vertical_spacing=0.07,
                        row_heights=[w / sum(weights) for w in weights],
                        subplot_titles=[r[0] for r in rows])
    for i, (row, dig) in enumerate(zip(rows, digital), 1):
        traces = row[1]
        if dig:
            offs = [(len(traces) - 1 - k) * 1.5 for k in range(len(traces))]
            for (name, y), o in zip(traces, offs):
                fig.add_scatter(x=t_ms[::step], y=y[::step] + o, name=name, mode="lines",
                                showlegend=False, row=i, col=1)
            fig.update_yaxes(tickmode="array", tickvals=[o + 0.5 for o in offs],
                             ticktext=[n for n, _ in traces], row=i, col=1)
        else:
            for name, y in traces:
                fig.add_scatter(x=t_ms[::step], y=y[::step], name=name, mode="lines", row=i, col=1)
    fig.update_xaxes(title_text="Time [ms]", row=len(rows), col=1)
    fig.update_layout(height=230 * len(rows) + 40 * sum(len(r[1]) for r, d in zip(rows, digital) if d),
                      margin=dict(t=40, b=10, l=10, r=10), legend=dict(orientation="h"))
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

def losses_plot(leg):
    devices = list(leg.keys())
    conduction = [c for c, w in leg.values()]
    switching = [w for c, w in leg.values()]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=devices,
            y=conduction,
            name="Conduction",
            marker_color="#1f77b4",
        )
    )
    fig.add_trace(
        go.Bar(
            x=devices,
            y=switching,
            name="Switching",
            marker_color="#ff7f0e",
        )
    )
    fig.update_layout(
        title="Loss breakdown",
        xaxis_title="Device",
        yaxis_title="Losses [W]",
        barmode="group",
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )

    return fig


def vector_plot(a, b, a_avg, b_avg, ref=None, vdc=None, unit="V"):
    """Space-vector plane. With vdc, draws the hexagon of the maximum vector and the linear-range circle."""
    fig = go.Figure()
    if vdc:
        k, th = np.arange(7) * np.pi / 3, np.linspace(0, 2 * np.pi, 200)
        fig.add_scatter(x=2 * vdc / 3 * np.cos(k), y=2 * vdc / 3 * np.sin(k), mode="lines",
                        name="hexagon", line=dict(dash="dot"))
        fig.add_scatter(x=vdc / np.sqrt(3) * np.cos(th), y=vdc / np.sqrt(3) * np.sin(th), mode="lines",
                        name="linear-range circle", line=dict(dash="dash"))
    fig.add_scatter(x=a[::8], y=b[::8], mode="markers", name="instantaneous", marker=dict(size=4, opacity=0.35))
    fig.add_scatter(x=a_avg[::8], y=b_avg[::8], mode="lines", name="carrier average")
    if ref is not None:
        fig.add_scatter(x=ref[0][::8], y=ref[1][::8], mode="lines", name="reference", line=dict(dash="dot"))
    fig.update_xaxes(title_text=f"\u03b1 [{unit}]")
    fig.update_yaxes(title_text=f"\u03b2 [{unit}]", scaleanchor="x", scaleratio=1)
    fig.update_layout(height=480, margin=dict(t=10, b=10, l=10, r=10), legend=dict(orientation="h"))
    return fig