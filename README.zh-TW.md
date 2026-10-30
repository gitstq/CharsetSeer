<div align="center">

# 🔍 CharsetSeer

**零依賴 · 離線優先的字元編碼偵測與亂碼修復引擎**

[简体中文](./README.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen?label=third--party)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-101%20passed-brightgreen)
![Offline](https://img.shields.io/badge/network-not%20required-orange)

</div>

---

## 🎉 專案介紹

你一定遇過這種情況：同事傳來一份檔案，打開卻是滿滿的 `鏂囧瓧` 或 `æ–‡å—`；日誌裡混著 `Ã©` 和 `Ð`；某個老專案的幾百個原始檔，誰也說不清哪些是 GBK、哪些是 UTF-8。

**CharsetSeer** 就是為了解決這件事而生的。它是一個**純 Python 標準函式庫實作**的字元編碼偵測與亂碼修復引擎：

- 🧭 **判得準** —— 不只問「能不能解碼」，還追問「解出來像不像人話」
- 🩹 **修得回** —— 自動推論當初誤用了哪種編碼，把亂碼還原成原文
- 📦 **裝得上** —— 零第三方依賴，一個 `pip install` 就能用，內網、離線、CI 全都沒問題
- 🔒 **靠得住** —— 不連網、不上傳、不落日誌，你的檔案內容不會離開本機

### 解決的痛點

| 痛點 | 傳統做法 | CharsetSeer |
| :--- | :--- | :--- |
| 打開就是亂碼 | 手動在編輯器裡一個個試編碼 | 一鍵判定 + 一鍵修復，還附上信心度 |
| 老專案編碼混雜 | 寫 `try/except` 硬猜 | 批次掃描目錄，輸出編碼分布表 |
| 批次轉碼怕改壞 | 直接覆蓋，壞了無法回溯 | `--dry-run` 預演 + `--backup` 備份 |
| 依賴太重裝不上 | 引入 `chardet` 等額外套件 | **零依賴**，標準函式庫即可執行 |
| 內網／離線環境 | 需要下載模型或詞庫 | 完全離線，所有碼表於執行期推導 |

### 自研差異化亮點

市面上已有 `chardet`、`charset-normalizer` 等優秀方案，CharsetSeer 的差異在於**三條自研判據**與**修復閉環**：

1. **🎯 中文超高頻字判據** —— 真實中文的前 900 個高頻字能覆蓋日常文本的八成以上，而「用錯誤編碼解碼」等於把位元組**隨機**映射到漢字，落在高頻字裡的機率很低。這條判據能把「真中文」與「看起來像中文的亂碼」乾淨地切開。
2. **🧬 主導文字一致性檢查** —— 一個自稱俄語的編碼若只解出零星幾個西里爾字母、其餘全是 ASCII，它幾乎肯定是把西歐重音字母誤讀成了西里爾。這條規則專治「零星重音字元引發的誤判」。
3. **🌐 UTF-8 動態語言推斷** —— UTF-8 是通用容器，可以裝中文、俄文、阿拉伯文。若給它固定一種語言歸屬，它解出的文字就拿不到契合度加成，反而會被「碰巧解出自己目標文字」的錯誤編碼壓過去。CharsetSeer 先解碼、再判斷裡面裝的到底是什麼語言，然後按該語言計分。
4. **♻️ 修復閉環** —— 偵測與修復共用同一套語言學證據，修復時還會以**語言中立的自然度評分**比較候選結果，避免「越修越糟」。

### 靈感來源

感謝 `chardet`、`charset-normalizer`、`file` 等前輩工具在編碼識別領域的長期累積。CharsetSeer 參考的是它們**解決的問題**（而非程式碼），並在中文／CJK 場景的準確性、零依賴可攜性、以及亂碼可逆修復這三個方向上做了獨立的實作與優化。

---

## ✨ 核心特性

### 🔤 編碼偵測

- 🎯 **涵蓋 17 種候選編碼**：UTF-8/16/32、GB18030（相容 GBK/GB2312）、Big5、Shift_JIS、EUC-JP、EUC-KR、KOI8-R、CP1250-1256、ISO-8859-7、Latin-1
- 📊 **輸出信心度**：不只是給個答案，還告訴你這個答案有多可信（0.00 ~ 1.00）
- 🔍 **可解釋**：`--explain` 輸出全部候選編碼的計分明細，包含字元類別分布與漢字熟悉度
- ⚡ **大檔案友善**：預設只取前 256 KB 取樣，幾 GB 的日誌也能秒出結果
- 🏷️ **語言歸屬**：順帶推測文本語言（簡體中文／繁體中文／日文／韓文／俄文／希臘文／阿拉伯文等）

### 🩹 亂碼修復

- 🔁 **自動推論誤用編碼**：枚舉（誤用編碼, 真實編碼）組合，以語言學證據挑最優解
- 🔄 **多輪修復**：處理被反覆錯誤轉碼的文本（最多 3 輪）
- 🛡️ **不會亂改**：文本本身正常時回傳「未修改」，絕不猜測式改寫
- 📈 **亂碼可能性評估**：`mojibake_likelihood()` 給出 0.00 ~ 1.00 的亂碼機率
- 🧪 **位元組無損原則**：只在位元組未遺失時修復；遇到 U+FFFD 等不可逆情況會明確告知

### 🔧 轉碼與 BOM

- 🔄 **批次轉碼**：單一檔案或整個目錄，一次性統一為目標編碼
- 🧷 **BOM 三種策略**：`keep`（保留）／`add`（新增）／`remove`（移除）
- 💾 **安全寫入**：`--backup` 產生 `.bak` 備份，`--dry-run` 只預演不落盤
- 🧯 **容錯可控**：`--on-error` 指定 `strict`／`replace`／`ignore` 處理策略

### 📦 工程化

- 🪶 **零第三方依賴**：僅使用 Python 標準函式庫
- 🖥️ **全平台**：Windows / macOS / Linux，Python 3.8+
- 🧪 **101 項單元測試**：涵蓋常規樣本、短文本、邊界輸入與 CLI 全流程
- 📤 **多種輸出格式**：`text`（對齊表格）／`json`（程式消費）／`csv`（試算表軟體）
- 🐍 **CLI + 函式庫雙用**：命令列即用，也可 `import charsetseer` 二次開發
- 📐 **型別提示齊備**：隨套件附帶 `py.typed`

---

## 🚀 快速開始

### 📋 環境需求

| 項目 | 需求 |
| :--- | :--- |
| Python | **3.8 以上** |
| 作業系統 | Windows / macOS / Linux（純 Python，無平台相關程式碼） |
| 第三方依賴 | **無** |
| 網路 | **不需要**（完全離線執行） |

### 📥 安裝

```bash
# 方式一：從 PyPI 安裝（推薦）
pip install charsetseer

# 方式二：從原始碼安裝
git clone https://github.com/gitstq/CharsetSeer.git
cd CharsetSeer
pip install -e .

# 方式三：不安裝，直接用（clone 後設定 PYTHONPATH）
export PYTHONPATH=$(pwd)
python3 -m charsetseer --help
```

### ✅ 驗證安裝

```bash
charsetseer --version
# charsetseer 1.0.0

charsetseer codecs
```

### 🎯 三分鐘上手

```bash
# 1️⃣ 偵測單一檔案的編碼
charsetseer detect README.md

# 2️⃣ 看看它為什麼這麼判斷（輸出全部候選計分）
charsetseer detect --explain mystery.txt

# 3️⃣ 修復一段亂碼
charsetseer fix 'ä¸­æå­ç¼ç æ£æµå·¥å·'
# ✨ 修復後：中文编码检测工具

# 4️⃣ 掃描整個專案，看看編碼分布
charsetseer scan ./src --summary

# 5️⃣ 批次轉成 UTF-8（先預演，確認無誤再執行）
charsetseer convert ./src --to utf-8 --dry-run
charsetseer convert ./src --to utf-8 --backup
```

### 🐍 作為函式庫使用

```python
from charsetseer import detect, detect_file, repair, convert_file

# 偵測位元組串
result = detect("中文編碼偵測工具".encode("gb18030"))
print(result.encoding)     # gb18030
print(result.confidence)   # 0.93
print(result.language)     # zh-hans

# 偵測檔案
detection, candidates = detect_file("data.csv", explain=True)

# 修復亂碼
broken = "中文編碼偵測工具".encode("utf-8").decode("latin-1")  # 模擬誤讀
fixed = repair(broken)
print(fixed.repaired)       # 中文編碼偵測工具
print(fixed.wrong_encoding) # latin-1
print(fixed.true_encoding)  # utf-8

# 轉碼（先用 dry_run 預演）
convert_file("legacy.txt", "utf-8", dry_run=True)
convert_file("legacy.txt", "utf-8", backup=True)
```

---

## 📖 詳細使用指南

### 🔍 `detect` —— 偵測編碼

```bash
charsetseer detect [PATH...] [--explain] [--format text|json] [--preview N]
```

| 參數 | 說明 |
| :--- | :--- |
| `PATH...` | 檔案路徑；**省略或使用 `-` 則讀取標準輸入** |
| `--explain` | 輸出全部候選編碼的計分明細 |
| `--format` | `text`（預設）或 `json` |
| `--preview` | 文本預覽長度，預設 200 |

```bash
# 單一檔案
charsetseer detect data.csv

# 多個檔案
charsetseer detect a.txt b.txt c.txt

# 管線輸入
curl -s https://example.com/page.html | charsetseer detect -

# JSON 輸出，便於指令碼消費
charsetseer detect --format json data.csv

# 查看計分明細
charsetseer detect --explain mystery.txt
```

<details>
<summary>📄 點擊展開：<code>--explain</code> 輸出範例</summary>

```
📄 檔案：mystery.txt
🔤 編碼：gb18030
📊 信心度：0.93 (很高)  ███████████░
🌐 語言：zh-hans
📌 BOM：無
📦 位元組數：16
👀 預覽：中文编码检测工具

編碼                     得分        信心度      可解碼      漢字熟悉度
--------------------------------------------------------
gb18030             5.142       0.93        是       1.00
big5                2.870       0.00        是       0.25
cp1251              1.879       0.00        是       0.00
utf-8                 N/A       0.00        否       0.00
```

> 「漢字熟悉度」指解碼出的漢字落在该編碼常用字庫中的比例。
> 熟悉度低 = 解出來的是罕用字 = 大概率是亂碼。

</details>

### 📂 `scan` —— 批次掃描目錄

```bash
charsetseer scan DIR [--include GLOB] [--exclude GLOB] [--max-size N]
                     [--limit N] [--summary] [--format text|json|csv]
```

| 參數 | 說明 |
| :--- | :--- |
| `--include` | 只掃描符合的檔名，**可重複指定** |
| `--exclude` | 排除符合的檔名，可重複指定 |
| `--max-size` | 跳過超過該大小的檔案，預設 32 MB |
| `--limit` | 最多掃描多少個檔案 |
| `--summary` | 額外輸出編碼分布彙總 |
| `--format` | `text`（預設）／`json`／`csv` |

```bash
# 掃描整個專案
charsetseer scan ./src

# 只看 Python 檔案，並統計編碼分布
charsetseer scan ./src --include '*.py' --summary

# 匯出 CSV，用 Excel 開啟分析
charsetseer scan ./src --format csv > encodings.csv

# 排除測試目錄
charsetseer scan . --exclude 'test_*' --exclude '*.min.js'
```

> 💡 **自動跳過**：`.git`、`node_modules`、`__pycache__` 等目錄，以及
> 圖片／影音／壓縮檔／PDF 等二進位副檔名（`--max-size` 之外的另一層保護）。

<details>
<summary>📄 點擊展開：<code>scan --summary</code> 輸出範例</summary>

```
檔案                   編碼       信心度  等級  位元組
---------------------  ---------  ----  ----  --
./src/main.py         utf-8      1.00  確定  1024
./src/legacy.py       gb18030    0.95  很高   856
./src/jp.txt          shift_jis  0.99  確定   412

📈 彙總：3 個檔案，0 個錯誤，共 2292 位元組
編碼                  檔案數
utf-8                 1
gb18030               1
shift_jis             1
```

</details>

### 🩹 `fix` —— 修復亂碼

```bash
charsetseer fix [TEXT] [--file PATH] [--in-place] [--aggressive] [--format text|json]
```

| 參數 | 說明 |
| :--- | :--- |
| `TEXT` | 待修復文本；**省略則讀取標準輸入** |
| `--file` | 從檔案讀取待修復文本 |
| `--in-place` | 搭配 `--file`，把修復結果寫回檔案 |
| `--aggressive` | 提升不明顯時仍強制嘗試（結果供人工確認） |
| `--format` | `text`（預設）或 `json` |

```bash
# 直接修復一段文本
charsetseer fix 'ä¸­æå­'

# 從管線讀入
cat broken.txt | charsetseer fix

# 修復檔案並寫回
charsetseer fix --file broken.txt --in-place

# JSON 輸出
charsetseer fix 'æå­åãæ¤åº' --format json
```

> ⚠️ **重要：並非所有亂碼都能修復。**
> 若當初誤讀時產生了 `U+FFFD`（取代字元），位元組資訊已經**不可逆遺失**，
> CharsetSeer 會明確告知「未發現可信的修復方案」，而不是給你一個似是而非的結果。

### 🔄 `convert` —— 批次轉碼

```bash
charsetseer convert PATH... --to ENC [--from ENC] [--bom keep|add|remove]
                            [--backup] [--dry-run] [--on-error strict|replace|ignore]
                            [--include GLOB] [--exclude GLOB]
```

| 參數 | 說明 |
| :--- | :--- |
| `--to` | **必填**，目標編碼 |
| `--from` | 來源編碼；省略則自動偵測 |
| `--bom` | BOM 策略：`keep`（預設）／`add`／`remove` |
| `--backup` | 寫入前產生 `.bak` 備份 |
| `--dry-run` | 只回報將發生的變更，**不寫入磁碟** |
| `--on-error` | 編解碼失敗處理策略，預設 `replace` |

```bash
# ⚠️ 強烈建議：先預演
charsetseer convert ./docs --to utf-8 --dry-run

# 確認無誤後再執行，並保留備份
charsetseer convert ./docs --to utf-8 --backup

# 轉碼並統一新增 BOM（配合某些 Windows 工具鏈）
charsetseer convert ./docs --to utf-8 --bom add

# 移除 BOM（配合 Unix 工具鏈／避免 BOM 混入檔案內容）
charsetseer convert ./docs --to utf-8 --bom remove

# 明確指定來源編碼，跳過自動偵測
charsetseer convert legacy.txt --from gbk --to utf-8
```

### 🏷️ `bom` —— BOM 偵測

```bash
charsetseer bom file1.txt file2.txt [--format json]
```

### 📜 `codecs` —— 查看支援的編碼

```bash
charsetseer codecs
```

### 🐍 Python API 總覽

```python
from charsetseer import (
    # —— 偵測 ——
    detect, detect_bytes, detect_file, guess_language,
    # —— 亂碼修復 ——
    repair, repair_bytes, mojibake_likelihood, looks_like_mojibake, naturalness,
    # —— 轉碼 ——
    convert_file, resolve_encoding, has_bom, strip_bom,
    # —— 掃描 ——
    scan_directory, scan_file, summarize,
)

# ① 偵測位元組串，回傳 Detection 物件
result = detect(raw_bytes)
result.encoding      # 'gb18030'
result.confidence    # 0.93
result.language      # 'zh-hans'
result.has_bom       # False
result.byte_length   # 1024
result.text_preview  # '中文編碼偵測工具...'

# ② 附候選明細
detection, candidates = detect_bytes(raw, explain=True)
for c in sorted(candidates, key=lambda x: -x.score):
    print(c.encoding, c.score, c.decodable, c.hanzi_familiarity)

# ③ 修復亂碼，回傳 RepairResult
fixed = repair(broken_text)
fixed.ok              # True
fixed.repaired        # '中文編碼偵測工具'
fixed.wrong_encoding  # 'latin-1'
fixed.true_encoding   # 'utf-8'
fixed.confidence      # 0.98
fixed.steps           # ['第 1 輪：以 latin-1 重新編碼 -> 以 utf-8 解碼...']

# ④ 判斷是否像亂碼
looks_like_mojibake("ä¸­æå­")    # True
mojibake_likelihood("正常中文")     # 0.0

# ⑤ 掃描目錄
reports = scan_directory("./src", include=["*.py"])
for r in reports:
    print(r.path, r.encoding, r.confidence)
print(summarize(reports))   # 編碼分布統計

# ⑥ 轉碼（支援 dry_run / backup / BOM 策略）
convert_file("a.txt", "utf-8", dry_run=True)
convert_file("a.txt", "utf-8", backup=True, bom_policy="add")
```

### 🎬 展示

> 📷 **螢幕截圖／展示動圖佔位**
>
> 此處預計補充：終端機 `detect --explain` 輸出截圖、`fix` 即時修復動圖、
> `scan --summary` 編碼分布視覺化。歡迎 PR 補充素材 🙌

---

## 💡 設計思路與迭代規劃

### 🏗️ 架構總覽

```
charsetseer/
├── __init__.py      # 公開 API 出口
├── __main__.py      # python -m charsetseer
├── cli.py           # 命令列：detect / scan / fix / convert / bom / codecs
├── detector.py      # 偵測引擎：BOM → ASCII → UTF-8 → 多候選語言學計分
├── tables.py        # 編碼特徵表、字頻表、權重與先驗（全部執行期推導）
├── mojibake.py      # 亂碼偵測與多輪修復
├── converter.py     # 轉碼、BOM 策略、備份與 dry-run
├── scanner.py       # 目錄遍歷與過濾
├── report.py        # text / json / csv 渲染
└── models.py        # Detection / Candidate / RepairResult / FileReport ...
```

### 🧠 偵測流程：證據強度由高到低，逐級收斂

```
   輸入位元組
      │
      ▼
  ① BOM 指紋 ──────► 命中即定案（信心度 1.00）
      │ 未命中
      ▼
  ② 純 ASCII ──────► 無歧義（信心度 0.99）
      │ 否
      ▼
  ③ UTF-8 嚴格驗證 ─► UTF-8 具自我校驗特性，隨機位元組能合法解碼的機率極低
      │
      ▼
  ④ 多候選語言學計分
      ├─ 位元組結構快篩（EUC 系列次位元組必須 ≥ 0xA1）
      ├─ 嚴格解碼（失敗即淘汰）
      ├─ 字元類別加權（漢字 / 假名 / 西里爾 / 拉丁 ...）
      ├─ 🧬 主導文字一致性檢查（零星目標文字 → 稀疏懲罰）
      ├─ 🎯 中文超高頻字判據（真中文 vs 亂碼漢字）
      ├─ 俄語字母頻率判據（區分 cp1251 / koi8-r）
      ├─ 專屬字元判據（cp1254 的 Ğ/ğ/İ/ı/Ş/ş 等）
      └─ 編碼先驗（johab 等罕見編碼降權）
      │
      ▼
   最高分者勝出 → 由分差與絕對品質推導信心度
```

### 🎯 為什麼「高頻字」比「常用字」更有效？

這是本專案最關鍵的一次設計取捨。

最初的實作以「解碼出的漢字是否屬於 GB2312 一級字庫（3755 字）」作為判據，結果**準確率只有 40%**。原因很直接：

> 一級字庫有 3755 個字，覆蓋面太廣 —— 用錯誤編碼解碼韓文或俄文時，
> 隨機映射出來的漢字**恰好也有很高比例落在這個集合裡**，
> 於是「亂碼」和「真中文」拿到了一樣的熟悉度分數，判別能力被徹底瓦解。

改成**只統計前 900 個超高頻字**之後，情況完全不同：真實中文的高頻字命中率通常在 60% 以上，而隨機解碼的命中率不到 15%。兩者的分布幾乎不重疊，判據一下子變得極其鋒利。

一句話總結：**判據的區分度，取決於正負樣本在該判據上的分布是否分離，而不是判據本身的「合理性」看起來有多強。**

### ⚖️ 偵測計分與修復計分為什麼要分開？

這也是一個踩過坑的點。

偵測引擎的權重裡，漢字權重（2.0）明顯高於拉丁字母（0.8）—— 這對**區分編碼**是必要的，因為「能解出漢字」正是區分 GBK 與 ASCII 的關鍵特徵。

但修復場景要比較的是**不同語言的正常文本**：`Café déjà vu` 與 `Caf泰 d泰j淌 vu` 誰更正常？若沿用偵測權重，任何「能解出漢字」的錯誤修復都會系統性地勝出。

因此 `mojibake.py` 另建了一套**語言中立的自然度評分**：只統計「不該出現的字元」（控制字元、取代字元、私用區、罕用漢字）與「各自語言的常見字元」，不預設任何語言偏好，再扣除亂碼特徵分。

### 🗺️ 迭代規劃

| 版本 | 計畫內容 |
| :--- | :--- |
| **v1.1** | 支援自訂候選編碼優先順序；為 `scan` 增加並行加速 |
| **v1.2** | 增量式偵測（重用上次結論）；`--exclude-dir` 自訂排除目錄 |
| **v1.3** | 補充日語／韓語字頻表，提升東亞短文本準確率 |
| **v1.4** | 輸出 HTML 視覺化報告；支援 `--since` 只掃描變更檔案 |
| **v2.0** | 可選的統計語言模型外掛（仍保持零**強制**依賴） |

### 🤝 社群貢獻方向

- 🌍 補充更多語言的字頻／字母頻率表
- 🧪 補充真實世界的亂碼樣本（尤其是小語種）
- ⚡ 效能優化（大目錄並行掃描）
- 📷 補充文件中的螢幕截圖與展示動圖
- 🌐 更多語言的 README 翻譯（日語／韓語／西班牙語）

---

## 📦 打包與部署指南

本專案屬於**命令列工具 + Python 函式庫**，無需打包成平台可執行檔。以下為完整的建置、安裝與發布流程。

### 🛠️ 建置 wheel 與 sdist

```bash
# 方式一：一鍵指令碼（會先跑測試）
./scripts/build.sh            # Linux / macOS / WSL
scripts\build.bat             # Windows

# 方式二：跳過測試快速建置
./scripts/build.sh --no-test

# 方式三：標準工具鏈
python3 -m pip install build
python3 -m build --wheel --sdist
```

產物位於 `dist/`：

```
dist/charsetseer-1.0.0-py3-none-any.whl   # 純 Python 通用 wheel，全平台可用
dist/charsetseer-1.0.0.tar.gz             # 原始碼發布包
```

> ✅ `py3-none-any` 表示**不依賴任何特定平台或 ABI**，一份 wheel 通吃
> Windows / macOS / Linux。

### 📥 安裝產物

```bash
# 安裝 wheel
pip install dist/charsetseer-1.0.0-py3-none-any.whl

# 可編輯模式（開發用）
pip install -e .

# 帶可選的開發依賴
pip install -e ".[dev]"
```

### 🚀 發布到 PyPI

```bash
# 1. 建置
./scripts/build.sh

# 2. 校驗產物
python3 -m twine check dist/*

# 3. 上傳到 TestPyPI 演練
python3 -m twine upload --repository testpypi dist/*

# 4. 正式發布
python3 -m twine upload dist/*
```

### 🧪 執行測試

```bash
# 標準函式庫 unittest，無需安裝 pytest
python3 -m unittest discover -s tests -v

# 或
make test
```

目前狀態：**101 項測試全部通過**，涵蓋：

- ✅ 19 種編碼的判定正確性（含常規樣本與短文本）
- ✅ 邊界輸入（空檔案、單一位元組、純二進位、混合內容）
- ✅ 亂碼修復的正向與「不應修改」反向案例
- ✅ 轉碼的 dry-run / backup / BOM 三種策略
- ✅ CLI 全流程與結束碼

### 🐳 其他部署型態

```bash
# 單一目錄免安裝執行（適合受限環境）
# 只要把 charsetseer/ 目錄複製到目標機器即可
python3 -m charsetseer detect target.txt

# 打包進你自己的專案（零依賴，直接 vendor 也無衝突）
cp -r charsetseer /path/to/your/project/
```

### 🔧 相容性說明

| 環境 | 狀態 |
| :--- | :--- |
| Python 3.8 / 3.9 / 3.10 / 3.11 / 3.12 | ✅ 支援 |
| Windows / macOS / Linux | ✅ 支援 |
| 離線 / 內網環境 | ✅ 支援（無需連網） |
| PyPy | ✅ 理論支援（純 Python 實作） |

---

## 🤝 貢獻指南

歡迎任何形式的貢獻！無論是回報 Bug、改進文件，還是提交程式碼。

### 🐛 提交 Issue

提交前請先搜尋現有 Issue 避免重複。回報時請包含：

1. **環境資訊**：Python 版本、作業系統、CharsetSeer 版本
2. **重現步驟**：可執行的最小範例
3. **期望行為** vs **實際行為**
4. **樣本資料**：如涉及具體檔案，請提供能重現的最小位元組樣本（可用 `xxd` 或 base64 給出）

> 🔒 **隱私提醒**：提交樣本前請務必去識別化，不要包含真實業務資料、金鑰或個人資訊。

### 🔀 提交 Pull Request

```bash
# 1. Fork 本倉庫並 clone
git clone https://github.com/<你的使用者名稱>/CharsetSeer.git
cd CharsetSeer

# 2. 建立特性分支
git checkout -b feat/your-feature

# 3. 開發與自測
python3 -m unittest discover -s tests -v

# 4. 提交（遵循 Angular 提交規範）
git commit -m "feat: 新增某某功能"
git commit -m "fix: 修復某某問題"
git commit -m "docs: 更新 README 的某某章節"

# 5. 推送並發起 PR
git push origin feat/your-feature
```

### 📐 提交資訊規範

遵循 **Angular 提交規範**：

| 前綴 | 用途 |
| :--- | :--- |
| `feat:` | 新增功能 |
| `fix:` | 修復問題 |
| `docs:` | 文件更新 |
| `refactor:` | 程式碼重構（不改變外部行為） |
| `perf:` | 效能優化 |
| `test:` | 測試相關 |
| `chore:` | 建置流程或輔助工具變動 |

### ✅ PR 檢查清單

- [ ] 程式碼可通過 `python3 -m unittest discover -s tests -v`（**101 項全部通過**）
- [ ] 新增功能配有對應的單元測試
- [ ] **未引入任何第三方執行時依賴**（這是本專案的核心承諾）
- [ ] 公開函式帶有型別提示與中文 docstring
- [ ] 必要時同步更新了 README（含簡中／繁中／英文三個版本）
- [ ] 提交資訊符合 Angular 規範

### 🎨 程式碼風格

- 遵循 PEP 8，使用 4 空格縮排
- 公開 API 必須帶 docstring（中文優先，便於社群閱讀）
- 關鍵設計取捨請在註解裡**寫明原因**，而不只是寫「做了什麼」
- 魔術數字請提取為 `tables.py` 中的具名常數，並附上取值理由

---

## 📄 開源協議說明

本專案基於 **MIT License** 開源，詳見 [LICENSE](./LICENSE) 檔案。

```
MIT License

Copyright (c) 2026 CharsetSeer Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
...
```

**簡而言之：**

- ✅ 允許商業使用、修改、散布、私有化部署
- ✅ 允許用於閉源專案
- ⚠️ 需保留原始版權聲明與許可聲明
- ❌ 作者不承擔任何明示或暗示的擔保責任

### 🙏 致謝

- 感謝 `chardet`、`charset-normalizer` 等前輩專案在編碼識別領域的探索與啟發
- 感謝 Python 標準函式庫 `codecs` 提供的完備編碼基礎設施 —— 本專案所有碼表均由它於執行期推導，這也是「零依賴」得以成立的前提
- 感謝所有提交 Issue 與 PR 的社群成員

---

<div align="center">

**如果 CharsetSeer 幫你省下了排查亂碼的時間，歡迎 Star ⭐ 支持一下！**

[⬆ 回到頂部](#-charsetseer)

</div>
