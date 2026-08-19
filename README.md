# 大學歷年錄取分數 Race

Bar chart race of Taiwan university admission scores, 民國 101–115 學年度.
Two views in one page: 台大各系 (within NTU) and 跨校同系 (same department
across 47 universities — all public schools plus the major private ones).
Data from www.com.tw 分發榜單 pages. Local-only.

## Use

Open `index.html` in a browser. Switch views with the tabs.

- 播放／暫停 ＋ 年份拉桿, smooth interpolation (~2s per year)
- 顯示前 N 名（預設 30，可選全部）
- 台大各系: 組別篩選 理組／文組／醫學／其他（預設理＋醫）
- 跨校同系: 科系下拉單選（預設資訊工程）＋ 公立／私立篩選

## Files

| File | What |
|---|---|
| `index.html` | The page (markup + CSS) |
| `app.js` | Race engine + the two view configs (vanilla JS, no deps) |
| `data.js` / `data-cross.js` | Embedded datasets, generated |
| `data/scores.csv` | NTU view table: 學年度, 校系代碼, 系名, 組別, 錄取平均, 原始總分 |
| `data/cross-scores.csv` | Cross view table: 學年度, 學校, 系名, 科系類型, 錄取平均, 原始總分 |
| `data/category-map.csv` | 系名 → 組別 (NTU view). **Edit to fix categories**, then rebuild |
| `data/dept-map.csv` | 系名 → 科系類型 (cross view). **Edit to fix grouping**, then rebuild |
| `data/raw/u1XX.html` | Raw NTU pages, one per year |
| `data/raw/cross/uCCC_YYY.html` | Raw pages per (school code, year) |
| `scripts/build_data.py` | Raw NTU pages → scores.csv + data.js |
| `scripts/build_cross_data.py` | Raw cross pages → cross-scores.csv + data-cross.js |
| `scripts/fetch.js` | Fetches a com.tw page through its Cloudflare challenge |
| `CONTEXT.md` | Domain glossary |

## Rebuild data

```bash
python3 scripts/build_data.py        # NTU view
python3 scripts/build_cross_data.py  # cross view
```

Manual edits in the two `*-map.csv` files survive rebuilds (existing map wins
over auto rules). Department types need >= 5 schools to enter the selector
(`MIN_SCHOOLS` in build_cross_data.py).

## Add a new year (e.g. 116)

```bash
npm install patchright   # once, anywhere; also needs Google Chrome installed
node scripts/fetch.js "https://www.com.tw/exam/university_001_116.html" data/raw/u116.html false
# cross view: loop the school codes (ls data/raw/cross for the current set):
#   node scripts/fetch.js "https://www.com.tw/exam/university_CCC_116.html" data/raw/cross/uCCC_116.html false
# add 116 to YEARS in both build scripts, then rebuild.
```

## Add a school to the cross view

Find its code in `https://www.com.tw/cross/university_list115.html`, fetch its
year pages into `data/raw/cross/uCCC_YYY.html`, rebuild. Schools are discovered
from the files on disk; names come from each page's title. Optionally add a
short display name to `SHORT_NAMES` in `scripts/build_cross_data.py`.

## Gotchas learned the hard way

- **Cloudflare**: the site blocks curl, headless browsers, and plain
  playwright even headed. Only **patchright + real Chrome + headed** passes.
  A Chrome window pops up briefly per fetch — that is required.
- **CJK compatibility ideographs**: some pages encode 理/律/歷/數/療/… as
  compatibility codepoints (e.g. 理 = U+F9E4). They look identical but break
  string matching, silently splitting one 系 into two series. The shared
  parser (`scripts/comtw.py`) NFC-normalizes everything; keep that.
- **Score scale change**: 101–110 指考 (subjects out of 100), 111+ 分科測驗
  (60 級分制). Raw averages are shown as-is; the collective bar shrink at
  111 is expected and annotated on the page.
- **School renames/mergers**: school names come from each page's title, so
  renames split series automatically (交大→陽明交大 at 111 per the source,
  屏教大→屏東大, 北市教大→北市大, 竹教大 merged into 清大 after 105,
  025 陽明大學 ends at 109).
