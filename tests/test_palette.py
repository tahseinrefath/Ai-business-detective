"""The design uses ONLY: obsidian black, chrome silver (neutral greys/whites) and laser crimson.
This test scans every stylesheet, script, template and report for colours outside those three families."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [*ROOT.glob("static/css/*.css"), *ROOT.glob("static/js/*.js"), *ROOT.glob("templates/*.html"), ROOT / "src/reports/report_generator.py"]
HEX = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
RGB = re.compile(r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})")


def family(r, g, b):
    if max(r, g, b) <= 64:
        return "obsidian"
    if max(r, g, b) - min(r, g, b) <= 16:
        return "silver"
    if r >= 140 and g <= 100 and b <= 120 and r - g >= 90:
        return "crimson"
    return None


def colours(text):
    for m in HEX.finditer(text):
        h = m.group(1)
        h = "".join(c * 2 for c in h) if len(h) == 3 else h
        yield m.group(0), tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    for m in RGB.finditer(text):
        yield m.group(0), tuple(int(x) for x in m.groups())


def test_only_obsidian_silver_crimson():
    bad = []
    for f in FILES:
        for token, rgb in colours(f.read_text(encoding="utf-8")):
            if family(*rgb) is None:
                bad.append(f"{f.relative_to(ROOT)}: {token}")
    assert not bad, "Colours outside the palette:\n" + "\n".join(sorted(set(bad)))


def test_all_three_families_are_actually_used():
    seen = set()
    for token, rgb in colours((ROOT / "static/css/style.css").read_text(encoding="utf-8")):
        seen.add(family(*rgb))
    assert {"obsidian", "silver", "crimson"} <= seen


def test_no_theme_or_accent_switchers_left():
    for f in FILES:
        t = f.read_text(encoding="utf-8")
        assert "data-accent" not in t and "setAccent" not in t, f
