#!/usr/bin/env python3
"""Parse data/raw/cross/u{code}_{year}.html into:
  - data/cross-scores.csv   one row per (year, school, department)
  - data/dept-map.csv       editable 系名 -> 科系類型 map (manual edits win)
  - data-cross.js           embedded dataset for the cross-university view

A department type enters the page's selector only if >= MIN_SCHOOLS distinct
schools ever offered it.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comtw import parse_exam_page, school_name

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "cross"
SCORES_CSV = ROOT / "data" / "cross-scores.csv"
DEPT_MAP_CSV = ROOT / "data" / "dept-map.csv"
DATA_JS = ROOT / "data-cross.js"

YEARS = list(range(101, 116))
MIN_SCHOOLS = 5
NO_TYPE = ""

# School identity comes from each page's <title> (then-current name), so
# renames/mergers (交大->陽明交大, 屏教大->屏東大, ...) split series by the
# same policy as department renames. 公立 = name starts 國立 or contains 市立.
# Display short names, keyed by the 台-normalized full name (臺 -> 台).
SHORT_NAMES = {
    "國立台灣大學": "台大",
    "國立台灣師範大學": "台師大",
    "國立中興大學": "中興",
    "國立成功大學": "成大",
    "東吳大學": "東吳",
    "國立政治大學": "政大",
    "高雄醫學大學": "高醫",
    "中原大學": "中原",
    "東海大學": "東海",
    "國立清華大學": "清大",
    "中國醫藥大學": "中國醫",
    "國立交通大學": "交大",
    "國立陽明交通大學": "陽明交大",
    "淡江大學": "淡江",
    "逢甲大學": "逢甲",
    "國立中央大學": "中央",
    "輔仁大學": "輔仁",
    "國立陽明大學": "陽明",
    "中山醫學大學": "中山醫",
    "國立中山大學": "中山",
    "長庚大學": "長庚",
    "元智大學": "元智",
    "國立中正大學": "中正",
    "國立台北大學": "台北大",
    "台北醫學大學": "北醫",
    "國立台灣海洋大學": "海大",
    "國立高雄師範大學": "高師大",
    "國立彰化師範大學": "彰師大",
    "國立台北藝術大學": "北藝大",
    "國立台中教育大學": "中教大",
    "國立台北教育大學": "北教大",
    "國立台南大學": "台南大",
    "國立東華大學": "東華",
    "台北市立教育大學": "北市教大",
    "台北市立大學": "北市大",
    "國立屏東教育大學": "屏教大",
    "國立屏東大學": "屏東大",
    "國立新竹教育大學": "竹教大",
    "國立台東大學": "台東大",
    "國立體育大學": "國體大",
    "國立台灣藝術大學": "台藝大",
    "國立暨南國際大學": "暨南",
    "國立台灣體育運動大學": "台體大",
    "台北市立體育學院": "北市體院",
    "國立台南藝術大學": "南藝大",
    "國立嘉義大學": "嘉大",
    "國立高雄大學": "高雄大",
    "國立宜蘭大學": "宜蘭大",
    "國立聯合大學": "聯合大",
    "國立金門大學": "金門大",
}

# Ordered keyword rules, first match wins. Specific before generic
# (資訊管理 before 資訊工程 keyword overlap, 牙醫/獸醫 before 醫學系, ...).
DEPT_TYPE_RULES = [
    # Exclusions first: college-wide programs and lookalike names that would
    # otherwise be swallowed by a broader keyword below.
    ("不分系", NO_TYPE),
    ("學院學士班", NO_TYPE),
    ("客家", NO_TYPE),
    ("生物產業傳播", NO_TYPE),
    ("運動醫學", NO_TYPE),
    ("通訊工程", NO_TYPE),
    ("資訊管理", "資訊管理"),
    ("醫學工程", "生醫工程"),
    ("生物醫學工程", "生醫工程"),
    ("生醫工程", "生醫工程"),
    ("生物醫學", "生命科學"),
    ("農業經濟", "農業經濟"),
    ("農業化學", "農業化學"),
    ("應用數學", "數學"),
    ("應用化學", "化學"),
    ("應用物理", "物理"),
    ("牙醫", "牙醫"),
    ("獸醫", "獸醫"),
    ("中醫", "中醫"),
    ("醫學系", "醫學"),
    ("藥學", "藥學"),
    ("護理", "護理"),
    ("醫學檢驗", "醫檢"),
    ("醫技", "醫檢"),
    ("物理治療", "物理治療"),
    ("職能治療", "職能治療"),
    ("公共衛生", "公共衛生"),
    ("電機", "電機工程"),
    ("電子工程", "電子工程"),
    ("光電", "光電"),
    ("資訊工程", "資訊工程"),
    ("資訊科學", "資訊工程"),
    ("資工", "資訊工程"),
    ("機械", "機械工程"),
    ("化學工程", "化學工程"),
    ("化工", "化學工程"),
    ("土木", "土木工程"),
    ("材料", "材料"),
    ("工業工程", "工業工程"),
    ("工業與系統", "工業工程"),
    ("建築", "建築"),
    ("企業管理", "企業管理"),
    ("工商管理", "企業管理"),
    ("企管", "企業管理"),
    ("會計", "會計"),
    ("財務金融", "財務金融"),
    ("財金", "財務金融"),
    ("金融", "財務金融"),
    ("國際企業", "國際企業"),
    ("國際貿易", "國際企業"),
    ("國企", "國際企業"),
    ("經濟", "經濟"),
    ("統計", "統計"),
    ("法律", "法律"),
    ("政治", "政治"),
    ("外交", "政治"),
    ("心理", "心理"),
    ("社會工作", "社會工作"),
    ("社會福利", "社會工作"),
    ("社會學", "社會學"),
    ("社會系", "社會學"),
    ("中國文學", "中文"),
    ("中文", "中文"),
    ("國文", "中文"),
    ("外國語文", "外文"),
    ("英國語文", "外文"),
    ("英美語文", "外文"),
    ("英文", "外文"),
    ("英語", "外文"),
    ("日本語文", "日文"),
    ("日文", "日文"),
    ("日語", "日文"),
    ("歷史", "歷史"),
    ("哲學", "哲學"),
    ("數學", "數學"),
    ("物理學", "物理"),
    ("化學系", "化學"),
    ("生命科學", "生命科學"),
    ("生物學", "生命科學"),
    ("生物科學", "生命科學"),
    ("大氣", "大氣科學"),
    ("地質", "地質"),
    ("地理", "地理"),
    ("新聞", "新聞傳播"),
    ("傳播", "新聞傳播"),
    ("廣告", "新聞傳播"),
    ("廣播電視", "新聞傳播"),
]


def canon_school(full_name):
    return full_name.replace("臺", "台")


def school_label(full_name):
    canon = canon_school(full_name)
    return SHORT_NAMES.get(canon, canon.removeprefix("國立"))


def is_public(full_name):
    canon = canon_school(full_name)
    return canon.startswith("國立") or "市立" in canon


def rule_dept_type(name):
    return next(
        (dept for keyword, dept in DEPT_TYPE_RULES if keyword in name), NO_TYPE
    )


def load_dept_map():
    """Existing map wins over rules, so manual edits survive rebuilds."""
    if not DEPT_MAP_CSV.exists():
        return {}
    with DEPT_MAP_CSV.open(encoding="utf-8-sig") as f:
        return {
            row["系名"]: row["科系類型"]
            for row in csv.DictReader(f)
            if row.get("系名") is not None and row.get("科系類型") is not None
        }


def write_csv(path, header, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def parse_all():
    """Return {(code, year): (school full name, [row, ...])} for every
    fetched page in data/raw/cross, discovered by filename."""
    pages = {}
    for path in sorted(RAW_DIR.glob("u*_*.html")):
        code, year_str = path.stem[1:].split("_")
        year = int(year_str)
        if year not in YEARS:
            continue
        rows = parse_exam_page(path)
        full_name = school_name(path)
        if rows and full_name:
            pages[(code, year)] = (full_name, rows)
    return pages


def main():
    pages = parse_all()
    if not pages:
        sys.exit("ERROR: no pages parsed — run the fetch first")
    print(f"parsed {len(pages)} school-year pages")

    all_names = sorted({r["name"] for _, rows in pages.values() for r in rows})
    existing_map = load_dept_map()
    dept_map = {
        name: existing_map.get(name, rule_dept_type(name)) for name in all_names
    }
    write_csv(
        DEPT_MAP_CSV,
        ["系名", "科系類型"],
        [(name, dept_map[name]) for name in all_names],
    )

    # Keep only dept types offered by >= MIN_SCHOOLS distinct schools.
    schools_per_type = {}
    for (code, year), (_, rows) in pages.items():
        for r in rows:
            dept = dept_map[r["name"]]
            if dept:
                schools_per_type.setdefault(dept, set()).add(code)
    kept_types = sorted(
        (dept for dept, codes in schools_per_type.items()
         if len(codes) >= MIN_SCHOOLS),
        key=lambda dept: -len(schools_per_type[dept]),
    )
    print(f"dept types kept (>= {MIN_SCHOOLS} schools): {len(kept_types)}")

    score_rows = [
        (year, school_label(pages[(code, year)][0]), r["name"],
         dept_map[r["name"]], r["avg"], r["total"])
        for (code, year) in sorted(pages)
        for r in pages[(code, year)][1]
    ]
    write_csv(
        SCORES_CSV,
        ["學年度", "學校", "系名", "科系類型", "錄取平均", "原始總分"],
        score_rows,
    )

    # Bar identity = (school label, 系名); renamed/merged schools split at
    # the rename by design — same policy as department renames.
    series = {}
    for (code, year), (full_name, rows) in pages.items():
        label = school_label(full_name)
        pub = is_public(full_name)
        for r in rows:
            dept = dept_map[r["name"]]
            if dept not in kept_types:
                continue
            key = (label, r["name"])
            entry = series.setdefault(key, {
                "school": label,
                "pub": pub,
                "d": dept,
                "s": [None] * len(YEARS),
            })
            entry["s"][YEARS.index(year)] = r["avg"]

    items = [
        {"n": f"{school} {name}", **entry}
        for (school, name), entry in sorted(series.items())
    ]
    dept_types = [
        {"id": dept, "schools": len(schools_per_type[dept])}
        for dept in kept_types
    ]
    dataset = {"years": YEARS, "deptTypes": dept_types, "items": items}
    DATA_JS.write_text(
        "window.EXAM_CROSS_DATA = "
        + json.dumps(dataset, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )

    print(f"wrote {SCORES_CSV.relative_to(ROOT)} ({len(score_rows)} rows)")
    print(f"wrote {DEPT_MAP_CSV.relative_to(ROOT)} ({len(all_names)} names)")
    print(f"wrote {DATA_JS.relative_to(ROOT)} ({len(items)} series)")
    print("types:", ", ".join(f"{t['id']}({t['schools']})" for t in dept_types))


if __name__ == "__main__":
    main()
