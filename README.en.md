<div align="center">

# 🔍 CharsetSeer

**Zero-dependency, offline-first charset detection and mojibake repair engine**

[简体中文](./README.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen?label=third--party)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-101%20passed-brightgreen)
![Offline](https://img.shields.io/badge/network-not%20required-orange)

</div>

---

## 🎉 What it is

You know the drill. A colleague sends you a file and it opens as `鏂囧瓧`. Your logs are peppered with `Ã©` and `Ð`. Nobody on the team can say for sure which of the four hundred source files in that legacy project are GBK and which are UTF-8.

**CharsetSeer** exists for exactly that. It is a charset detection and mojibake repair engine built **entirely on the Python standard library**:

- 🧭 **Accurate** — it doesn't just ask "can this be decoded?", it asks "does what came out look like real language?"
- 🩹 **Reversible** — it figures out which codec was applied by mistake and turns the mojibake back into readable text
- 📦 **Installable anywhere** — zero third-party dependencies, so it works on air-gapped networks and locked-down CI images
- 🔒 **Private** — no network calls, no telemetry, no logging. Your file contents never leave the machine

### The problems it solves

| Problem | The usual workaround | With CharsetSeer |
| :--- | :--- | :--- |
| Opens as garbage | Cycle through encodings in your editor until one sticks | One command, plus a confidence score |
| Legacy project with mixed encodings | Hand-rolled `try/except` guessing | Scan the tree, get a distribution table |
| Afraid a bulk conversion will corrupt files | Overwrite in place and hope | `--dry-run` first, `--backup` always |
| Dependencies won't install | Pull in `chardet` and friends | **Zero dependencies** — stdlib only |
| No network access | Download a model or data tables | Fully offline; every table is derived at runtime |

### What makes it different

Good tools already exist in this space (`chardet`, `charset-normalizer`). CharsetSeer takes a different angle — three original heuristics plus a closed repair loop:

1. **🎯 Top-frequency Chinese characters.** The 900 most common Chinese characters cover well over 80% of everyday text. Decoding with the *wrong* codec is equivalent to mapping bytes onto characters at random, and random mappings land in that top-900 set only rarely. This separates genuine Chinese from "Chinese-looking garbage" far more cleanly than a mere "is this a valid character" test.
2. **🧬 Dominant-script consistency.** If a codec claiming to be Russian yields a handful of scattered Cyrillic letters while everything else is plain ASCII, it almost certainly misread Western accented letters as Cyrillic. This rule exists specifically to kill the "a few stray accented characters caused a wrong call" failure mode.
3. **🌐 Dynamic language inference for UTF-8.** UTF-8 is a universal container — it can hold Chinese, Russian, Arabic, anything. Pin it to one fixed language and its decoded text never earns any script-affinity bonus, so it loses to wrong codecs that happen to produce *their* target script. CharsetSeer decodes first, works out what language it actually contains, and then scores it with that language's weights.
4. **♻️ A closed repair loop.** Detection and repair share the same linguistic evidence. Repair additionally uses a **language-neutral naturalness score** to compare candidate outcomes, so a "fix" can never make things worse.

### Acknowledgements

Thanks to `chardet`, `charset-normalizer`, and the venerable `file` command for the groundwork in encoding detection. CharsetSeer borrows the **problem** they solve — not their code — and takes an independent approach on three axes: CJK accuracy, zero-dependency portability, and reversible mojibake repair.

---

## ✨ Features

### 🔤 Detection

- 🎯 **17 candidate encodings**: UTF-8/16/32, GB18030 (covers GBK/GB2312), Big5, Shift_JIS, EUC-JP, EUC-KR, KOI8-R, CP1250–1256, ISO-8859-7, Latin-1
- 📊 **Confidence scores** — not just an answer, but how much to trust it (0.00 – 1.00)
- 🔍 **Explainable** — `--explain` prints the full scorecard: per-codec scores, character-class breakdown, hanzi familiarity
- ⚡ **Large-file friendly** — samples the first 256 KB, so multi-gigabyte logs return instantly
- 🏷️ **Language hint** — Simplified Chinese, Traditional Chinese, Japanese, Korean, Russian, Greek, Arabic, and more

### 🩹 Mojibake repair

- 🔁 **Infers the mistaken codec** — enumerates (wrong, true) pairs and picks the best by linguistic evidence
- 🔄 **Multi-round** — handles text that was mis-transcoded more than once (up to 3 rounds)
- 🛡️ **Won't touch healthy text** — returns "not modified" rather than guessing
- 📈 **Mojibake likelihood** — `mojibake_likelihood()` returns a 0.00 – 1.00 probability
- 🧪 **Honest about irreversibility** — if the original misread produced `U+FFFD`, the bytes are gone and it says so

### 🔧 Conversion and BOM handling

- 🔄 **Bulk conversion** — a single file or an entire tree, normalised to a target encoding
- 🧷 **Three BOM policies** — `keep` / `add` / `remove`
- 💾 **Safe writes** — `--backup` writes `.bak` files, `--dry-run` previews without touching disk
- 🧯 **Configurable error handling** — `--on-error strict|replace|ignore`

### 📦 Engineering

- 🪶 **Zero third-party dependencies** — standard library only
- 🖥️ **Cross-platform** — Windows / macOS / Linux, Python 3.8+
- 🧪 **101 unit tests** — covering normal samples, short texts, edge inputs, and the full CLI
- 📤 **Three output formats** — `text` (aligned table), `json` (machine-readable), `csv` (spreadsheets)
- 🐍 **CLI and library** — usable from the shell or via `import charsetseer`
- 📐 **Fully typed** — ships a `py.typed` marker

---

## 🚀 Quick start

### 📋 Requirements

| Item | Requirement |
| :--- | :--- |
| Python | **3.8 or newer** |
| OS | Windows / macOS / Linux (pure Python, no platform-specific code) |
| Dependencies | **None** |
| Network | **Not required** (fully offline) |

### 📥 Install

```bash
# Option 1: from PyPI
pip install charsetseer

# Option 2: from source
git clone https://github.com/gitstq/CharsetSeer.git
cd CharsetSeer
pip install -e .

# Option 3: run without installing
export PYTHONPATH=$(pwd)
python3 -m charsetseer --help
```

### ✅ Verify

```bash
charsetseer --version
# charsetseer 1.0.0

charsetseer codecs
```

### 🎯 Three minutes to productive

```bash
# 1️⃣ Detect a single file
charsetseer detect README.md

# 2️⃣ See why it decided that (full candidate scorecard)
charsetseer detect --explain mystery.txt

# 3️⃣ Repair a piece of mojibake
charsetseer fix 'ä¸­æå­ç¼ç æ£æµå·¥å·'
# ✨ Repaired: 中文编码检测工具

# 4️⃣ Scan a project and see the encoding distribution
charsetseer scan ./src --summary

# 5️⃣ Bulk-convert to UTF-8 (preview first, then commit)
charsetseer convert ./src --to utf-8 --dry-run
charsetseer convert ./src --to utf-8 --backup
```

### 🐍 As a library

```python
from charsetseer import detect, detect_file, repair, convert_file

# Detect raw bytes
result = detect("中文编码检测工具".encode("gb18030"))
print(result.encoding)     # gb18030
print(result.confidence)   # 0.93
print(result.language)     # zh-hans

# Detect a file, with the candidate breakdown
detection, candidates = detect_file("data.csv", explain=True)

# Repair mojibake
broken = "中文编码检测工具".encode("utf-8").decode("latin-1")  # simulate a misread
fixed = repair(broken)
print(fixed.repaired)       # 中文编码检测工具
print(fixed.wrong_encoding) # latin-1
print(fixed.true_encoding)  # utf-8

# Convert (preview first)
convert_file("legacy.txt", "utf-8", dry_run=True)
convert_file("legacy.txt", "utf-8", backup=True)
```

---

## 📖 Usage guide

### 🔍 `detect` — identify an encoding

```bash
charsetseer detect [PATH...] [--explain] [--format text|json] [--preview N]
```

| Flag | Meaning |
| :--- | :--- |
| `PATH...` | File paths; **omit or pass `-` to read stdin** |
| `--explain` | Print the full candidate scorecard |
| `--format` | `text` (default) or `json` |
| `--preview` | Preview length, default 200 |

```bash
# One file
charsetseer detect data.csv

# Several files
charsetseer detect a.txt b.txt c.txt

# From a pipe
curl -s https://example.com/page.html | charsetseer detect -

# JSON, for scripting
charsetseer detect --format json data.csv

# Scorecard
charsetseer detect --explain mystery.txt
```

<details>
<summary>📄 Expand: sample <code>--explain</code> output</summary>

```
📄 文件：mystery.txt
🔤 编码：gb18030
📊 置信度：0.93 (很高)  ███████████░
🌐 语言：zh-hans
📌 BOM：无
📦 字节数：16
👀 预览：中文编码检测工具

编码                     得分        置信度      可解码      汉字熟悉度
--------------------------------------------------------
gb18030             5.142       0.93        是       1.00
big5                2.870       0.00        是       0.25
cp1251              1.879       0.00        是       0.00
utf-8                 N/A       0.00        否       0.00
```

> "汉字熟悉度" (hanzi familiarity) is the share of decoded Chinese characters
> that appear in that codec's common-character set. Low familiarity means
> rare characters came out — which almost always means it's mojibake.

</details>

### 📂 `scan` — scan a directory

```bash
charsetseer scan DIR [--include GLOB] [--exclude GLOB] [--max-size N]
                     [--limit N] [--summary] [--format text|json|csv]
```

| Flag | Meaning |
| :--- | :--- |
| `--include` | Only files matching this glob; **repeatable** |
| `--exclude` | Skip files matching this glob; repeatable |
| `--max-size` | Skip files larger than this, default 32 MB |
| `--limit` | Stop after N files |
| `--summary` | Also print the encoding distribution |
| `--format` | `text` (default) / `json` / `csv` |

```bash
# Scan a whole project
charsetseer scan ./src

# Python files only, with a distribution summary
charsetseer scan ./src --include '*.py' --summary

# Export CSV for a spreadsheet
charsetseer scan ./src --format csv > encodings.csv

# Skip test directories
charsetseer scan . --exclude 'test_*' --exclude '*.min.js'
```

> 💡 **Skipped automatically**: `.git`, `node_modules`, `__pycache__`, and
> binary extensions (images, audio/video, archives, PDFs) — a second layer of
> protection on top of `--max-size`.

<details>
<summary>📄 Expand: sample <code>scan --summary</code> output</summary>

```
文件                   编码       置信度  等级  字节
---------------------  ---------  ----  ----  --
./src/main.py         utf-8      1.00  确定  1024
./src/legacy.py       gb18030    0.95  很高   856
./src/jp.txt          shift_jis  0.99  确定   412

📈 汇总：3 个文件，0 个错误，共 2292 字节
编码                  文件数
utf-8                 1
gb18030               1
shift_jis             1
```

</details>

### 🩹 `fix` — repair mojibake

```bash
charsetseer fix [TEXT] [--file PATH] [--in-place] [--aggressive] [--format text|json]
```

| Flag | Meaning |
| :--- | :--- |
| `TEXT` | Text to repair; **omit to read stdin** |
| `--file` | Read the text to repair from a file |
| `--in-place` | With `--file`, write the repair back |
| `--aggressive` | Force an attempt even if the improvement is marginal (review the result) |
| `--format` | `text` (default) or `json` |

```bash
# Repair a literal string
charsetseer fix 'ä¸­æå­'

# From a pipe
cat broken.txt | charsetseer fix

# Repair a file in place
charsetseer fix --file broken.txt --in-place

# JSON output
charsetseer fix 'æå­åãæ¤åº' --format json
```

> ⚠️ **Not every mojibake can be repaired.**
> If the original misread produced `U+FFFD` replacement characters, the bytes
> are **irreversibly lost**. CharsetSeer tells you plainly that it found no
> trustworthy repair rather than handing you a plausible-looking fabrication.

### 🔄 `convert` — bulk transcode

```bash
charsetseer convert PATH... --to ENC [--from ENC] [--bom keep|add|remove]
                            [--backup] [--dry-run] [--on-error strict|replace|ignore]
                            [--include GLOB] [--exclude GLOB]
```

| Flag | Meaning |
| :--- | :--- |
| `--to` | **Required.** Target encoding |
| `--from` | Source encoding; auto-detected if omitted |
| `--bom` | BOM policy: `keep` (default) / `add` / `remove` |
| `--backup` | Write a `.bak` copy before overwriting |
| `--dry-run` | Report what would change **without writing** |
| `--on-error` | Error strategy, default `replace` |

```bash
# ⚠️ Strongly recommended: preview first
charsetseer convert ./docs --to utf-8 --dry-run

# Then commit, keeping backups
charsetseer convert ./docs --to utf-8 --backup

# Convert and add a BOM (for toolchains that expect one)
charsetseer convert ./docs --to utf-8 --bom add

# Strip BOMs (for Unix toolchains, or when the BOM leaks into content)
charsetseer convert ./docs --to utf-8 --bom remove

# Pin the source encoding and skip detection
charsetseer convert legacy.txt --from gbk --to utf-8
```

### 🏷️ `bom` — BOM check

```bash
charsetseer bom file1.txt file2.txt [--format json]
```

### 📜 `codecs` — supported encodings

```bash
charsetseer codecs
```

### 🐍 Full Python API

```python
from charsetseer import (
    # --- detection ---
    detect, detect_bytes, detect_file, guess_language,
    # --- mojibake ---
    repair, repair_bytes, mojibake_likelihood, looks_like_mojibake, naturalness,
    # --- conversion ---
    convert_file, resolve_encoding, has_bom, strip_bom,
    # --- scanning ---
    scan_directory, scan_file, summarize,
)

# 1) Detect bytes, returns a Detection
result = detect(raw_bytes)
result.encoding      # 'gb18030'
result.confidence    # 0.93
result.language      # 'zh-hans'
result.has_bom       # False
result.byte_length   # 1024
result.text_preview  # '中文编码检测工具...'

# 2) With the candidate breakdown
detection, candidates = detect_bytes(raw, explain=True)
for c in sorted(candidates, key=lambda x: -x.score):
    print(c.encoding, c.score, c.decodable, c.hanzi_familiarity)

# 3) Repair, returns a RepairResult
fixed = repair(broken_text)
fixed.ok              # True
fixed.repaired        # '中文编码检测工具'
fixed.wrong_encoding  # 'latin-1'
fixed.true_encoding   # 'utf-8'
fixed.confidence      # 0.98
fixed.steps           # ['第 1 轮：以 latin-1 重新编码 -> 以 utf-8 解码...']

# 4) Is it mojibake?
looks_like_mojibake("ä¸­æå­")    # True
mojibake_likelihood("正常中文")     # 0.0

# 5) Scan a directory
reports = scan_directory("./src", include=["*.py"])
for r in reports:
    print(r.path, r.encoding, r.confidence)
print(summarize(reports))   # encoding distribution

# 6) Convert (dry_run / backup / BOM policy)
convert_file("a.txt", "utf-8", dry_run=True)
convert_file("a.txt", "utf-8", backup=True, bom_policy="add")
```

### 🎬 Demo

> 📷 **Screenshot / GIF placeholder**
>
> Planned: terminal output of `detect --explain`, a live `fix` recording, and a
> visualisation of the `scan --summary` distribution. PRs with assets welcome 🙌

---

## 💡 Design notes and roadmap

### 🏗️ Structure

```
charsetseer/
├── __init__.py      # public API surface
├── __main__.py      # python -m charsetseer
├── cli.py           # CLI: detect / scan / fix / convert / bom / codecs
├── detector.py      # engine: BOM → ASCII → UTF-8 → multi-candidate scoring
├── tables.py        # codec profiles, frequency tables, weights, priors (all derived at runtime)
├── mojibake.py      # mojibake detection and multi-round repair
├── converter.py     # transcoding, BOM policy, backup, dry-run
├── scanner.py       # directory walking and filtering
├── report.py        # text / json / csv rendering
└── models.py        # Detection / Candidate / RepairResult / FileReport ...
```

### 🧠 Detection: strongest evidence first, narrowing as it goes

```
   input bytes
      │
      ▼
  ① BOM signature ───► a hit decides it outright (confidence 1.00)
      │ no hit
      ▼
  ② Pure ASCII ──────► unambiguous (confidence 0.99)
      │ no
      ▼
  ③ Strict UTF-8 ────► UTF-8 self-validates; random bytes almost never decode cleanly
      │
      ▼
  ④ Multi-candidate linguistic scoring
      ├─ byte-shape prefilter (EUC trail bytes must be ≥ 0xA1)
      ├─ strict decode (failure eliminates)
      ├─ character-class weighting (hanzi / kana / Cyrillic / Latin ...)
      ├─ 🧬 dominant-script consistency (scattered target script → sparsity penalty)
      ├─ 🎯 top-frequency Chinese character check (real Chinese vs. garbage hanzi)
      ├─ Russian letter-frequency check (separates cp1251 from koi8-r)
      ├─ exclusive-character check (cp1254's Ğ/ğ/İ/ı/Ş/ş and friends)
      └─ codec prior (rare codecs such as johab are penalised)
      │
      ▼
   highest score wins → confidence from the margin and absolute quality
```

### 🎯 Why top-frequency beats "is it a common character"

This was the single most important design decision in the project.

The first implementation scored "does the decoded character belong to GB2312 level 1 (3,755 characters)". **Accuracy was 40%.** The reason is straightforward:

> 3,755 characters is a wide net. When you decode Korean or Russian with the
> wrong codec, the resulting characters land inside that set at a high rate
> *by chance*. Genuine Chinese and mojibake ended up with the same familiarity
> score, and the heuristic collapsed.

Switching to **only the top 900 most frequent characters** changed everything. Real Chinese typically scores above 60% against that list; random decoding lands under 15%. The two distributions barely overlap, which makes the signal razor sharp.

The lesson: **a heuristic is only as good as the separation it produces between positive and negative samples — not how reasonable it sounds on paper.**

### ⚖️ Why detection and repair use different scoring

Another lesson learned the hard way.

In the detection weights, a Chinese character scores 2.0 while a Latin letter scores 0.8. That gap is *necessary* for distinguishing encodings — "it decoded into Chinese characters" is precisely what separates GBK from ASCII.

But repair compares two plausible pieces of ordinary text in *different languages*: is `Café déjà vu` or `Caf泰 d泰j淌 vu` the real one? Reusing the detection weights means any wrong repair that coughs up Chinese characters wins systematically.

So `mojibake.py` has its own **language-neutral naturalness score**. It only counts characters that shouldn't be there (control chars, replacement chars, private-use, rare hanzi) against characters that are common *in their own language*, with no language preference baked in, and then subtracts a mojibake-signature penalty.

### 🗺️ Roadmap

| Version | Planned |
| :--- | :--- |
| **v1.1** | User-configurable candidate priority; parallel scanning for `scan` |
| **v1.2** | Incremental detection (reuse prior results); `--exclude-dir` |
| **v1.3** | Japanese and Korean frequency tables for better East-Asian short-text accuracy |
| **v1.4** | HTML report output; `--since` to scan only changed files |
| **v2.0** | Optional statistical language-model plugin (still zero *mandatory* dependencies) |

### 🤝 Where contributions help most

- 🌍 Frequency tables for more languages
- 🧪 Real-world mojibake samples, especially for less-common languages
- ⚡ Performance work (parallel scanning of large trees)
- 📷 Screenshots and demo GIFs for the docs
- 🌐 More README translations (Japanese, Korean, Spanish)

---

## 📦 Packaging and deployment

CharsetSeer is a **CLI tool plus Python library**. There is no platform binary to build. The full build, install, and release flow follows.

### 🛠️ Build wheel and sdist

```bash
# Option 1: one-shot script (runs tests first)
./scripts/build.sh            # Linux / macOS / WSL
scripts\build.bat             # Windows

# Option 2: skip tests
./scripts/build.sh --no-test

# Option 3: standard toolchain
python3 -m pip install build
python3 -m build --wheel --sdist
```

Output lands in `dist/`:

```
dist/charsetseer-1.0.0-py3-none-any.whl   # pure-Python universal wheel
dist/charsetseer-1.0.0.tar.gz             # source distribution
```

> ✅ `py3-none-any` means **no platform or ABI is targeted** — one wheel covers
> Windows, macOS, and Linux.

### 📥 Install the artifacts

```bash
# Install the wheel
pip install dist/charsetseer-1.0.0-py3-none-any.whl

# Editable install (for development)
pip install -e .

# With optional dev extras
pip install -e ".[dev]"
```

### 🚀 Publish to PyPI

```bash
# 1. Build
./scripts/build.sh

# 2. Check the artifacts
python3 -m twine check dist/*

# 3. Rehearse on TestPyPI
python3 -m twine upload --repository testpypi dist/*

# 4. Publish
python3 -m twine upload dist/*
```

### 🧪 Run the tests

```bash
# stdlib unittest — no pytest needed
python3 -m unittest discover -s tests -v

# or
make test
```

Current status: **101 tests, all passing**, covering:

- ✅ Correct identification across 19 sample types (normal and short texts)
- ✅ Edge inputs (empty files, single bytes, pure binary, mixed content)
- ✅ Repair — both positive cases and "must not modify" negative cases
- ✅ Conversion — dry-run, backup, and all three BOM policies
- ✅ Full CLI flows and exit codes

### 🐳 Other deployment shapes

```bash
# Run without installing (good for locked-down environments):
# just copy the charsetseer/ directory to the target machine
python3 -m charsetseer detect target.txt

# Vendor it into your own project (zero deps, no conflicts)
cp -r charsetseer /path/to/your/project/
```

### 🔧 Compatibility

| Environment | Status |
| :--- | :--- |
| Python 3.8 / 3.9 / 3.10 / 3.11 / 3.12 | ✅ Supported |
| Windows / macOS / Linux | ✅ Supported |
| Offline / air-gapped networks | ✅ Supported (no network needed) |
| PyPy | ✅ Should work (pure Python) |

---

## 🤝 Contributing

Contributions of any shape are welcome — bug reports, documentation fixes, or code.

### 🐛 Filing an issue

Please search existing issues first. A useful report includes:

1. **Environment** — Python version, OS, CharsetSeer version
2. **Reproduction** — the smallest runnable example
3. **Expected** vs **actual** behaviour
4. **Sample data** — if a specific file is involved, the smallest byte sample that reproduces it (via `xxd` or base64)

> 🔒 **Privacy**: strip samples of real business data, keys, or personal
> information before posting.

### 🔀 Pull requests

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/CharsetSeer.git
cd CharsetSeer

# 2. Create a feature branch
git checkout -b feat/your-feature

# 3. Develop and test
python3 -m unittest discover -s tests -v

# 4. Commit (Angular convention)
git commit -m "feat: add some capability"
git commit -m "fix: correct some defect"
git commit -m "docs: update a README section"

# 5. Push and open a PR
git push origin feat/your-feature
```

### 📐 Commit message convention

Follow the **Angular commit convention**:

| Prefix | Use for |
| :--- | :--- |
| `feat:` | New functionality |
| `fix:` | Bug fixes |
| `docs:` | Documentation |
| `refactor:` | Restructuring without behaviour change |
| `perf:` | Performance work |
| `test:` | Tests |
| `chore:` | Build tooling and auxiliary changes |

### ✅ PR checklist

- [ ] `python3 -m unittest discover -s tests -v` passes (**all 101 tests**)
- [ ] New functionality comes with tests
- [ ] **No new third-party runtime dependency** (this is the project's core promise)
- [ ] Public functions carry type hints and a docstring
- [ ] READMEs updated where relevant (all three: Simplified, Traditional, English)
- [ ] Commit messages follow the Angular convention

### 🎨 Code style

- PEP 8, four-space indentation
- Docstrings on all public APIs
- In comments, explain **why** a design decision was made, not just what the code does
- Lift magic numbers into named constants in `tables.py`, with a note on how the value was chosen

---

## 📄 License

Released under the **MIT License**. See [LICENSE](./LICENSE) for the full text.

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

**In short:**

- ✅ Commercial use, modification, distribution, and private deployment allowed
- ✅ Usable in closed-source projects
- ⚠️ Keep the copyright and permission notice
- ❌ No warranty, express or implied

### 🙏 Thanks

- To `chardet` and `charset-normalizer` for the groundwork and inspiration in encoding detection
- To Python's `codecs` module — every code table in this project is derived from it at runtime, which is what makes "zero dependencies" possible at all
- To everyone who files issues and opens pull requests

---

<div align="center">

**If CharsetSeer saved you an afternoon of squinting at mojibake, consider leaving a star ⭐**

[⬆ Back to top](#-charsetseer)

</div>
