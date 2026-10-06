"""Schematics for the Theory page, drawn as inline SVG (pure Python, no dependencies).

The strokes use currentColor, so they follow the Streamlit theme (light or dark)."""
import math


def _svg(w, h, body, uid, x0=0):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} 0 {w - x0} {h}" width="100%" style="max-width:{w - x0}px" '
            'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            'font-family="sans-serif" font-size="14">'
            f'<defs><marker id="ar-{uid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor" stroke="none"/></marker></defs>'
            f'{body}</svg>')


def _t(x, y, s, anchor="middle", size=14, bold=False):
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    weight = ' font-weight="bold"' if bold else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size}" fill="currentColor" '
            f'stroke="none"{weight}>{s}</text>')


def _line(*pts, arrow=None, dash=False):
    extra = (f' marker-end="url(#ar-{arrow})"' if arrow else "") + (' stroke-dasharray="6 4"' if dash else "")
    return f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}"{extra}/>'


def _dot(x, y):
    return f'<circle cx="{x}" cy="{y}" r="3.5" fill="currentColor" stroke="none"/>'


def _ground(x, y):
    return (_line((x, y), (x, y + 8)) + _line((x - 9, y + 8), (x + 9, y + 8)) + _line((x - 6, y + 13), (x + 6, y + 13))
            + _line((x - 3, y + 18), (x + 3, y + 18)))


def _source(x, y, label, side="left"):
    lx, anchor = (x - 22, "end") if side == "left" else (x + 22, "start")
    return f'<circle cx="{x}" cy="{y}" r="15"/>' + _t(x, y + 5, "+") + _t(lx, y + 5, label, anchor)


def _resistor(x, y, w=40, label="R"):
    return f'<rect x="{x}" y="{y - 10}" width="{w}" height="20"/>' + _t(x + w / 2, y - 16, label)


def _inductor(x, y, label="L", bumps=4):
    path = f"M{x},{y} " + " ".join("a7.5,7.5 0 0 1 15,0" for _ in range(bumps))
    return f'<path d="{path}"/>' + _t(x + 7.5 * bumps, y - 16, label)


def _leg(x, yc, names):
    """One inverter leg: two switches with antiparallel diodes. Rails at yc -/+ 110, pole at (x, yc)."""
    top, bot, s = yc - 110, yc + 110, []
    for y0, name in ((top + 25, names[0]), (yc + 25, names[1])):
        xd, y1 = x + 38, y0 + 45
        s += [f'<rect x="{x - 15}" y="{y0}" width="30" height="45" rx="4"/>', _t(x, y0 + 28, name, size=13),
              _line((x, y0), (xd, y0), (xd, y0 + 10)), _line((xd - 8, y0 + 10), (xd + 8, y0 + 10)),
              f'<polygon points="{xd - 8},{y0 + 32} {xd + 8},{y0 + 32} {xd},{y0 + 10}"/>',
              _line((xd, y0 + 32), (xd, y1), (x, y1))]
    s += [_line((x, top), (x, top + 25)), _line((x, top + 70), (x, yc + 25)), _line((x, yc + 70), (x, bot)), _dot(x, yc)]
    return "".join(s)


def half_bridge():
    s = [_line((50, 40), (50, 80)), _source(50, 95, "V_dc/2"), _line((50, 110), (50, 190)), _source(50, 205, "V_dc/2"),
         _line((50, 220), (50, 260)), _line((50, 40), (230, 40)), _line((50, 260), (230, 260)), _dot(50, 150),
         _line((50, 150), (28, 150)), _ground(28, 150), _t(14, 176, "0", "end"),
         _leg(230, 150, ("S1", "S2")), _t(212, 142, "A", "end", bold=True),
         _line((230, 150), (300, 150)), _resistor(300, 150), _line((340, 150), (350, 150)), _inductor(350, 150),
         _line((410, 150), (430, 150), (430, 185)), _ground(430, 185),
         _t(300, 215, "v_A0 = \u00b1V_dc/2", "start"), _t(300, 236, "(pole voltage, referred to 0)", "start", 12)]
    return _svg(480, 285, "".join(s), "half", x0=-45)


def full_bridge():
    s = [_line((50, 40), (50, 134)), _source(50, 150, "V_dc"), _line((50, 166), (50, 260)),
         _line((50, 40), (330, 40)), _line((50, 260), (330, 260)),
         _leg(170, 150, ("S1", "S2")), _leg(330, 150, ("S3", "S4")),
         _t(152, 142, "A", "end", bold=True), _t(348, 142, "B", "start", bold=True),
         _line((170, 150), (200, 150)), _resistor(200, 150), _line((240, 150), (250, 150)), _inductor(250, 150),
         _line((310, 150), (330, 150)), _t(250, 292, "v_AB = v_A0 \u2212 v_B0", "middle"),
         _t(250, 312, "bipolar: \u00b1V_dc    unipolar: +V_dc, 0, \u2212V_dc", "middle", 12)]
    return _svg(480, 325, "".join(s), "full", x0=-45)


def three_phase():
    s = [_line((50, 40), (50, 134)), _source(50, 150, "V_dc"), _line((50, 166), (50, 260)),
         _line((50, 40), (330, 40)), _line((50, 260), (330, 260))]
    for x, k, names in ((130, "a", ("S1", "S4")), (230, "b", ("S3", "S6")), (330, "c", ("S5", "S2"))):
        s += [_leg(x, 150, names), _line((x, 150), (x + 34, 150)), _t(x + 44, 154, k, "start", bold=True)]
    for y, k in ((95, "a"), (150, "b"), (205, "c")):
        s += [_t(455, y + 4, k, "end", bold=True), _line((462, y), (480, y)), _resistor(480, y, 36, "Z"),
              _line((516, y), (545, y))]
    s += [_line((545, 95), (545, 205)), _dot(545, 150), _t(558, 154, "N", "start", bold=True),
          _t(500, 245, "star load, isolated neutral", "middle", 12), _t(500, 262, "(terminals a, b, c = the poles)", "middle", 12)]
    return _svg(600, 285, "".join(s), "three", x0=-45)


def modulator():
    def box(x, y, w, h, l1, l2=None):
        out = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>'
        return out + (_t(x + w / 2, y + h / 2 - 3, l1) + _t(x + w / 2, y + h / 2 + 15, l2, size=12) if l2
                      else _t(x + w / 2, y + h / 2 + 5, l1))
    s = [box(10, 15, 140, 50, "Reference", "m_a sin(\u03c9t)"), box(10, 95, 140, 50, "Carrier", "triangle / sawtooth"),
         box(200, 45, 110, 60, "Comparator", "v_ref > v_car"), box(360, 45, 100, 60, "Dead time", "t_d on turn-on"),
         box(510, 45, 100, 60, "Gates", "S+  and  S\u2212"), box(660, 45, 120, 60, "Leg", "v_A0 = \u00b1V_dc/2"),
         _line((150, 40), (175, 40), (175, 62), (198, 62), arrow="mod"), _line((150, 120), (175, 120), (175, 88), (198, 88), arrow="mod"),
         _line((310, 75), (358, 75), arrow="mod"), _line((460, 75), (508, 75), arrow="mod"), _line((610, 75), (658, 75), arrow="mod"),
         _t(255, 125, "natural: continuous", "middle", 11), _t(255, 140, "regular: sampled", "middle", 11)]
    return _svg(790, 160, "".join(s), "mod")


def hexagon():
    cx, cy, R = 260, 235, 165
    p = lambda a, r=R: (cx + r * math.cos(math.radians(a)), cy - r * math.sin(math.radians(a)))
    codes = ["100", "110", "010", "011", "001", "101"]
    s = [f'<polygon points="{" ".join("%.1f,%.1f" % p(60 * k) for k in range(6))}"/>']
    for k in range(6):
        s.append(_line((cx, cy), p(60 * k)))
        x, y = p(60 * k, R + 22)
        s.append(_t(x, y + 4, f"V{k + 1} ({codes[k]})", "start" if k == 0 else "end" if k == 3 else "middle", 13))
        x, y = p(60 * k + 30, 0.8 * R)
        s.append(_t(x, y + 5, ["I", "II", "III", "IV", "V", "VI"][k], "middle", 15, True))
    s.append(f'<circle cx="{cx}" cy="{cy}" r="{R * math.sqrt(3) / 2:.1f}" stroke-dasharray="6 4"/>')
    s += [_dot(cx, cy), _t(cx, cy + 40, "V0, V7", "middle", 11), _t(cx, cy + 54, "(000, 111)", "middle", 11),
          _t(cx, 468, "dashed circle: linear limit |v_ref| \u2264 V_dc / \u221a3", "middle", 12)]
    phi, mag = 38, 0.55 * R
    a = mag * math.sin(math.radians(60 - phi)) / math.sin(math.radians(60))
    b = mag * math.sin(math.radians(phi)) / math.sin(math.radians(60))
    p1 = (cx + a, cy)
    p2 = (p1[0] + b * math.cos(math.radians(60)), p1[1] - b * math.sin(math.radians(60)))
    s += [_line((cx, cy), p1, arrow="hex"), _line(p1, p2, arrow="hex"), _line((cx, cy), p2, arrow="hex"),
          _t((cx + p1[0]) / 2, cy + 18, "T1\u00b7V1", "middle", 12), _t(p1[0] + 36, (p1[1] + p2[1]) / 2 + 8, "T2\u00b7V2", "start", 12),
          _t(p2[0], p2[1] - 12, "v_ref", "middle", 12, True)]
    return _svg(520, 480, "".join(s), "hex")


def thermal_network():
    s = []
    for y, x0, name, label in ((70, 45, "P_T(t)", "Z_th,T"), (140, 95, "P_D(t)", "Z_th,D")):
        s += [f'<circle cx="{x0}" cy="{y}" r="15"/>', _line((x0, y + 9), (x0, y - 9), arrow="th"), _t(x0, y - 24, name, "middle", 12),
              _line((x0 + 15, y), (170, y)), _dot(x0 + 70 if y == 70 else 140, y), f'<rect x="170" y="{y - 15}" width="100" height="30" rx="4"/>',
              _t(220, y + 5, label), _line((270, y), (330, y)), _line((x0, y + 15), (x0, 232))]
    s += [_t(100, 62, "Tj,T", "middle", 12), _t(145, 132, "Tj,D", "middle", 12),
          _line((330, 70), (330, 140)), _dot(330, 105), _t(345, 100, "T_hs", "start", 13, True), _line((330, 140), (330, 170)),
          '<rect x="305" y="170" width="50" height="36" rx="4"/>', _t(330, 193, "R_sa"), _line((330, 206), (330, 232)),
          _line((45, 232), (400, 232)), _ground(220, 232), _t(250, 268, "T_amb", "start", 13, True),
          _t(300, 12, "Z_th = R_jc / (1 + s\u03c4)   (R_jc in parallel with C_th)", "middle", 12)]
    return _svg(520, 290, "".join(s), "th")