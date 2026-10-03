"""Regenerate the README screenshots from the running app.

One-time setup:   pip install playwright pillow && playwright install chromium
Run from the repo root:   python scripts/make_screenshots.py
"""
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
PORT = 8599
BASE = f"http://localhost:{PORT}"
WIDTH = 1500  # default viewport width


def select(page, label, option):
    page.get_by_label(label, exact=True).click()
    page.get_by_role("option", name=option, exact=True).click()
    page.wait_for_timeout(1200)


def toggle_load(page):
    page.get_by_test_id("stCheckbox").get_by_text("Series R-L load").click()
    page.wait_for_timeout(1500)


def tab(page, name):
    page.get_by_role("tab", name=name).click()
    page.wait_for_timeout(1200)


def slider_steps(page, label, key, n):
    page.get_by_role("slider", name=label).focus()
    for _ in range(n):
        page.keyboard.press(key)
    page.wait_for_timeout(1500)


def crop(path, margin=24):
    """Cut the empty area under the content (the viewport is taller than the page).
    Only the main area is inspected: the sidebar has its own background and always reaches the bottom."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    bg = img.getpixel((w - 4, h - 4))
    last = max(y for y in range(h) if any(img.getpixel((x, y)) != bg for x in range(int(w * 0.35), w - 8, 5)))
    img.crop((0, 0, w, min(h, last + margin))).save(path, optimize=True)


SHOTS = [
    # name, path, viewport height, actions[, viewport width]
    ("three_phase_waveforms", "/Three_Phase", 2400,
     lambda p: (toggle_load(p), select(p, "Modulation", "SVPWM"))),
    ("clarke_park", "/Three_Phase", 1250,
     lambda p: (toggle_load(p), select(p, "Modulation", "SVPWM"), tab(p, "Clarke / Park"))),
    ("half_bridge_sawtooth", "/Half_Bridge", 1500,
     lambda p: (toggle_load(p), select(p, "Carrier", "Sawtooth rising"))),
    ("modulation_comparison", "/Modulation_Comparison", 1750, lambda p: None, 1700),
    ("sweeps", "/Sweeps", 1500, lambda p: None, 1700),
    ("svpwm", "/SVPWM", 1300, lambda p: slider_steps(p, "Carrier period to inspect", "ArrowRight", 8)),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "Home.py", "--server.headless", "true",
                               "--server.port", str(PORT), "--browser.gatherUsageStats", "false"],
                              cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"{BASE}/_stcore/health", timeout=1)
                break
            except Exception:
                time.sleep(1)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            for name, path, height, actions, *width in SHOTS:
                page = browser.new_page(viewport={"width": width[0] if width else WIDTH, "height": height},
                                        color_scheme="light")
                page.goto(BASE + path)
                page.wait_for_selector('[data-testid="stSidebar"]')
                page.wait_for_selector(".js-plotly-plot, [data-testid='stDataFrame']", timeout=60000)
                actions(page)
                page.wait_for_timeout(2500)  # let the charts settle
                target = OUT / f"{name}.png"
                page.screenshot(path=str(target))
                crop(target)
                print("saved", target.relative_to(ROOT))
                page.close()
            browser.close()
    finally:
        server.terminate()


if __name__ == "__main__":
    main()