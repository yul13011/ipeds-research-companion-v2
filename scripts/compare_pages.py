"""Part 6b check: version 1 and version 2 side by side, one screenshot of each screen and state in both, compared
pixel by pixel. A development tool (Playwright, requirements-dev.txt); never run on the host.

    .venv\\Scripts\\python.exe scripts/compare_pages.py --v1 http://127.0.0.1:8516 --v2 http://127.0.0.1:8517

Both apps must already be running. Typed questions call the model in both apps (a few cents); the Explore examples
call it in version 2 only (version 1 runs them as fixed plans). Screenshots and difference images go to
logs/screens; the summary (share of pixels that differ, and where) to logs/screens/summary.csv.
"""
import argparse
import csv
import time
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "logs" / "screens"
SIZE = dict(width=1440, height=900)


def settle(page, extra=1.0):
    """Wait until Streamlit has finished running the script (and any model call), then a little longer for layout."""
    page.wait_for_selector('[data-testid="stApp"]', timeout=60000)
    time.sleep(0.8)
    for _ in range(360):
        running = page.locator('[data-testid="stStatusWidget"]').is_visible() or page.locator('[data-testid="stSpinner"]').count()             or page.get_by_text("Stop", exact=True).is_visible()
        if not running:
            break
        time.sleep(0.5)
    time.sleep(extra)


def click(page, name, nth=0):
    page.get_by_role("button", name=name, exact=True).nth(nth).click()
    settle(page)


def ask(page, question, wait=2.0):
    box = page.locator('[data-testid="stChatInputTextArea"]')
    box.fill(question)
    box.press("Enter")
    settle(page, wait)


def to_chat(page):
    click(page, "Ask & Analyze")


def definitions(page):
    """Version 1 hides the definitions browser behind development mode (About); version 2 shows it to everyone."""
    to_chat(page)
    if not page.get_by_role("button", name="Search definitions →").count():
        click(page, "About this prototype")
        page.get_by_text("Enable development mode").click()
        settle(page)
        click(page, "← Back to conversation")
    click(page, "Search definitions →")
    click(page, "Search codebooks")


# Each state: (name, steps from a fresh page). The same steps are run against both apps.
STATES = [
    ("01_explore", lambda p: None),
    ("02_explore_topic_open", lambda p: click(p, "Explore topic →", 0)),
    ("03_chat_empty", to_chat),
    ("04_chat_menu_hidden", lambda p: (to_chat(p), click(p, "Hide Menu"))),
    ("05_chat_side_panels_collapsed", lambda p: (to_chat(p), click(p, "‹"), click(p, "›"))),
    ("06_answer_with_table", lambda p: (to_chat(p), click(p, "What was Yale’s admission rate in fall 2024?"))),
    ("07_answer_with_chart", lambda p: (to_chat(p), click(p, "Show Yale, Harvard, and Princeton admission rates from 2015 through 2024."))),
    ("08_school_picker", lambda p: (to_chat(p), ask(p, "What is Columbia's admission rate?"))),
    ("09_clarifying_question", lambda p: (to_chat(p), ask(p, "How many faculty does Yale have?"))),
    ("10_decline", lambda p: (to_chat(p), ask(p, "What is the average starting salary of Yale graduates?"))),
    ("11_definitions_browser", definitions),
    ("12_about", lambda p: click(p, "About this prototype")),
]


def shoot(url, tag, only=None):
    shots = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for name, steps in STATES:
            if only and name not in only:
                continue
            page = browser.new_page(viewport=SIZE)
            page.goto(url)
            settle(page)
            try:
                steps(page)
                path = OUT / f"{name}_{tag}.png"
                page.screenshot(path=str(path))
                shots[name] = path
            except Exception as e:                      # a state one app cannot reach (for example v1's tools panel)
                print(f"{tag} {name}: {type(e).__name__}: {str(e).splitlines()[0]}")
            page.close()
        browser.close()
    return shots


def compare(a, b, name):
    one, two = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    if one.size != two.size:
        two = two.resize(one.size)
    diff = ImageChops.difference(one, two)
    mask = diff.convert("L").point(lambda v: 255 if v > 24 else 0)
    share = sum(1 for v in mask.get_flattened_data() if v) / (one.size[0] * one.size[1])
    box = mask.getbbox()
    marked = Image.blend(one, Image.new("RGB", one.size, (255, 0, 0)), 0.0)
    marked.paste((255, 0, 0), mask=mask)
    marked.save(OUT / f"{name}_diff.png")
    return round(100 * share, 2), box


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1", default="http://127.0.0.1:8516")
    ap.add_argument("--v2", default="http://127.0.0.1:8517")
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    one, two = shoot(args.v1, "v1", args.only), shoot(args.v2, "v2", args.only)
    rows = []
    for name, _ in STATES:
        if name in one and name in two:
            share, box = compare(one[name], two[name], name)
            rows.append(dict(state=name, pixels_differing_percent=share, region=box))
        else:
            rows.append(dict(state=name, pixels_differing_percent=None, region="missing in " + ("v1" if name not in one else "v2")))
        print(rows[-1])
    with open(OUT / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["state", "pixels_differing_percent", "region"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
