# 台灣大學錄取分數排名 Race

用 bar chart race 動畫呈現大學分發入學錄取分數的變化，民國 101–115 學年度。
一頁兩個視圖：**台大各系**（校內比較）與**跨校同系**（47 間大學比同一科系，
涵蓋全部國立、市立大學與主要私立大學）。資料來自 www.com.tw 分發榜單。
純靜態網頁，不需要伺服器。

🔗 線上版：https://a7512cs.github.io/tw-university-ranking-race/

## 使用

用瀏覽器打開 `index.html`（或上面的線上連結），上方分頁切換視圖。

- 播放／暫停 ＋ 年份拉桿，年與年之間平滑過渡（每年約 2 秒）
- 顯示前 N 名（預設 20，可選到全部）
- 台大各系：組別篩選 理組／文組／醫學／其他（預設理＋醫）
- 跨校同系：科系下拉單選（預設資訊工程）＋ 公立／私立篩選

## 檔案說明

| 檔案 | 內容 |
|---|---|
| `index.html` | 網頁（排版 + 樣式） |
| `app.js` | Race 動畫引擎與兩個視圖設定（純 vanilla JS，零依賴） |
| `data.js` / `data-cross.js` | 網頁讀的資料檔，由 build 腳本產生 |
| `data/scores.csv` | 台大視圖資料表：學年度、校系代碼、系名、組別、錄取平均、原始總分 |
| `data/cross-scores.csv` | 跨校視圖資料表：學年度、學校、系名、科系類型、錄取平均、原始總分 |
| `data/category-map.csv` | 系名 → 組別（台大視圖）。**想改分類就改這個**，改完重跑 build |
| `data/dept-map.csv` | 系名 → 科系類型（跨校視圖）。**想改歸併就改這個**，改完重跑 build |
| `data/raw/`（不在 repo 內） | 抓下來的原始網頁，一頁一檔 |
| `scripts/build_data.py` | 原始網頁 → scores.csv + data.js |
| `scripts/build_cross_data.py` | 原始網頁 → cross-scores.csv + data-cross.js |
| `scripts/fetch.js` | 穿過 Cloudflare 驗證抓 com.tw 頁面 |
| `CONTEXT.md` | 領域詞彙表 |

## 重建資料

```bash
python3 scripts/build_data.py        # 台大視圖
python3 scripts/build_cross_data.py  # 跨校視圖
```

兩個 `*-map.csv` 的手動修改會保留（既有對照優先於自動規則）。
科系類型要出現在 ≥5 間學校才會進選單（`build_cross_data.py` 的 `MIN_SCHOOLS`）。

## 新增年度（例如 116）

```bash
npm install patchright   # 裝一次即可；另需已安裝 Google Chrome
node scripts/fetch.js "https://www.com.tw/exam/university_001_116.html" data/raw/u116.html false
# 跨校視圖：對每個學校代碼抓一頁（現有代碼看 data/raw/cross 的檔名）：
#   node scripts/fetch.js "https://www.com.tw/exam/university_CCC_116.html" data/raw/cross/uCCC_116.html false
# 兩個 build 腳本的 YEARS 各加上 116，然後重跑。
```

## 新增學校（跨校視圖）

到 `https://www.com.tw/cross/university_list115.html` 查學校代碼，把該校各年頁面
抓進 `data/raw/cross/uCCC_YYY.html`，重跑 build 即可。學校清單由檔案自動發現、
校名讀自每頁標題；想要短一點的顯示名稱，可在 `scripts/build_cross_data.py` 的
`SHORT_NAMES` 加一筆。

## 踩過的坑

- **Cloudflare**：該網站擋 curl、headless 瀏覽器、甚至一般 playwright（headed 也擋）。
  只有 **patchright ＋ 真 Chrome ＋ headed 模式**過得了，抓的時候會短暫彈出
  Chrome 視窗，屬正常現象。
- **CJK 相容表意字**：部分頁面把 理／律／歷／數／療 等字編成相容碼位
  （如 理 = U+F9E4），肉眼看起來一樣但字串比對不相等，會把同一個系
  默默拆成兩條序列。共用解析器（`scripts/comtw.py`）已做 NFC 正規化，
  動解析器時務必保留。
- **量尺變更**：101–110 指考（每科滿分 100）、111 起分科測驗（每科 60 級分制）。
  分數照原始值顯示，播到 111 年全場集體縮短是預期行為，頁面上有標註。
- **學校改名／合併**：校名讀自每頁當年的標題，改名自動斷開序列
  （交大→陽明交大在來源網站是 111 年切換、屏教大→屏東大、北市教大→北市大、
  竹教大 105 後併入清大、025 陽明大學到 109 為止）。
