"""Shared parser for www.com.tw exam pages (各系組錄取分數)."""
import html as htmllib
import re
import unicodedata

TITLE_PATTERN = re.compile(r"<title>\s*([^<]+?)\s*-")
SCORE_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)\s*\((\d+(?:\.\d+)?)\)$")
CODE_PATTERN = re.compile(r"\((\d{4})\)")
TAG_PATTERN = re.compile(r"<[^>]+>")
CELL_PATTERN = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def school_name(path):
    """Full school name for that year, from the page <title> (e.g.
    國立臺灣大學). Renamed/merged schools carry their then-current name."""
    raw = unicodedata.normalize(
        "NFC", path.read_text(encoding="utf-8", errors="ignore")
    ).replace("﻿", "")
    match = TITLE_PATTERN.search(raw)
    return match.group(1).strip() if match else ""


def parse_exam_page(path):
    """Return list of dicts {code, name, total, avg} for one school-year page.

    NFC: the site mixes CJK compatibility ideographs (理=U+F9E4, 歷=U+F98C,
    ...) into some pages; without folding them the same 系 splits into two
    visually identical series.
    """
    raw = unicodedata.normalize(
        "NFC", htmllib.unescape(path.read_text(encoding="utf-8", errors="ignore"))
    )
    rows = []
    for block in re.split(r"<tr[^>]*>", raw):
        code_match = CODE_PATTERN.search(block)
        if not code_match:
            continue
        texts = [
            TAG_PATTERN.sub("", cell).replace("\xa0", " ").strip()
            for cell in CELL_PATTERN.findall(block)
        ]
        texts = [t for t in texts if t]
        score_match = next(
            (m for t in texts if (m := SCORE_PATTERN.match(t))), None
        )
        name = texts[1] if len(texts) > 1 else ""
        if not score_match or not name or name == "榜單查詢":
            continue
        rows.append({
            "code": code_match.group(1),
            "name": name,
            "total": float(score_match.group(1)),
            "avg": float(score_match.group(2)),
        })
    return rows
