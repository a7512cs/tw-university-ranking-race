#!/usr/bin/env python3
"""Parse data/raw/u*.html (com.tw exam pages) into:
  - data/scores.csv        merged table, one row per (year, department)
  - data/category-map.csv  editable 系名 -> 組別 map (manual edits win)
  - data.js                embedded dataset for index.html
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comtw import parse_exam_page

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
SCORES_CSV = ROOT / "data" / "scores.csv"
CATEGORY_MAP_CSV = ROOT / "data" / "category-map.csv"
DATA_JS = ROOT / "data.js"

YEARS = list(range(101, 116))
CATEGORIES = ("理組", "文組", "醫學", "其他")
FALLBACK_CATEGORY = "其他"

# Ordered keyword rules, first match wins. Specific keywords must come
# before shorter ones they contain (e.g. 牙醫/獸醫 before 醫學系).
CATEGORY_RULES = [
    ("醫學工程", "理組"),      # 工學院
    ("農業經濟", "理組"),      # 生農學院
    ("農業化學", "理組"),      # 生農學院
    ("資訊管理", "文組"),      # 管理學院
    ("牙醫", "醫學"),
    ("獸醫", "理組"),          # 獸醫專業學院
    # 醫學院
    ("醫學系", "醫學"),
    ("藥學", "醫學"),
    ("護理", "醫學"),
    ("醫學檢驗", "醫學"),
    ("物理治療", "醫學"),
    ("職能治療", "醫學"),
    # 文學院
    ("中國文學", "文組"),
    ("外國語文", "文組"),
    ("歷史", "文組"),
    ("哲學", "文組"),
    ("人類學", "文組"),
    ("圖書資訊", "文組"),
    ("日本語文", "文組"),
    ("戲劇", "文組"),
    # 社科、法律、管理學院
    ("政治學", "文組"),
    ("經濟", "文組"),
    ("社會工作", "文組"),
    ("社會學", "文組"),
    ("法律", "文組"),
    ("工商管理", "文組"),
    ("會計", "文組"),
    ("財務金融", "文組"),
    ("國際企業", "文組"),
    # 理學院
    ("數學", "理組"),
    ("物理學", "理組"),
    ("化學系", "理組"),
    ("地質", "理組"),
    ("心理", "理組"),
    ("地理環境資源", "理組"),
    ("大氣科學", "理組"),
    # 工學院、電資學院
    ("土木", "理組"),
    ("機械", "理組"),
    ("化學工程", "理組"),
    ("工程科學及海洋工程", "理組"),
    ("材料科學", "理組"),
    ("電機工程", "理組"),
    ("資訊工程", "理組"),
    # 生農學院
    ("農藝", "理組"),
    ("生物環境系統", "理組"),
    ("森林", "理組"),
    ("動物科學", "理組"),
    ("園藝", "理組"),
    ("生物產業傳播", "理組"),
    ("生物機電", "理組"),
    ("生物產業機電", "理組"),
    ("昆蟲", "理組"),
    ("植物病理", "理組"),
    # 公衛學院、生命科學院
    ("公共衛生", "理組"),
    ("生命科學", "理組"),
    ("生化科技", "理組"),
]

def rule_category(name):
    return next(
        (cat for keyword, cat in CATEGORY_RULES if keyword in name),
        FALLBACK_CATEGORY,
    )


def load_category_map():
    """Existing map wins over rules, so manual edits survive rebuilds."""
    if not CATEGORY_MAP_CSV.exists():
        return {}
    with CATEGORY_MAP_CSV.open(encoding="utf-8-sig") as f:
        return {
            row["系名"]: row["組別"]
            for row in csv.DictReader(f)
            if row.get("系名") and row.get("組別") in CATEGORIES
        }


def write_csv(path, header, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main():
    by_year = {}
    for year in YEARS:
        path = RAW_DIR / f"u{year}.html"
        if not path.exists():
            print(f"WARNING: {path.name} missing, year {year} skipped")
            continue
        rows = parse_exam_page(path)
        if not rows:
            print(f"WARNING: {path.name} parsed 0 rows")
            continue
        by_year[year] = rows
        print(f"{year}: {len(rows)} rows")

    if not by_year:
        sys.exit("ERROR: no data parsed")

    all_names = sorted({r["name"] for rows in by_year.values() for r in rows})
    existing_map = load_category_map()
    category_map = {
        name: existing_map.get(name, rule_category(name)) for name in all_names
    }
    for name in [n for n in all_names if n not in existing_map]:
        if category_map[name] == FALLBACK_CATEGORY:
            print(f"REVIEW: no rule matched 「{name}」 -> {FALLBACK_CATEGORY}")

    write_csv(
        CATEGORY_MAP_CSV,
        ["系名", "組別"],
        [(name, category_map[name]) for name in all_names],
    )

    score_rows = [
        (year, r["code"], r["name"], category_map[r["name"]], r["avg"], r["total"])
        for year in sorted(by_year)
        for r in by_year[year]
    ]
    write_csv(
        SCORES_CSV,
        ["學年度", "校系代碼", "系名", "組別", "錄取平均", "原始總分"],
        score_rows,
    )

    years = sorted(by_year)
    avg_lookup = {
        (year, r["name"]): r["avg"] for year in years for r in by_year[year]
    }
    items = [
        {
            "n": name,
            "c": category_map[name],
            "s": [avg_lookup.get((year, name)) for year in years],
        }
        for name in all_names
    ]
    dataset = {"years": years, "items": items}
    DATA_JS.write_text(
        "window.EXAM_DATA = " + json.dumps(dataset, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )

    print(f"\nwrote {SCORES_CSV.relative_to(ROOT)} ({len(score_rows)} rows)")
    print(f"wrote {CATEGORY_MAP_CSV.relative_to(ROOT)} ({len(all_names)} names)")
    print(f"wrote {DATA_JS.relative_to(ROOT)} ({len(years)} years)")


if __name__ == "__main__":
    main()
