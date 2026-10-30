<div align="center">

# 🔍 CharsetSeer

**零依赖 · 离线优先的字符编码检测与乱码修复引擎**

[简体中文](./README.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen?label=third--party)
![License](https://img.shields.io/badge/license-MIT-green)
![Tests](https://img.shields.io/badge/tests-101%20passed-brightgreen)
![Offline](https://img.shields.io/badge/network-not%20required-orange)

</div>

---

## 🎉 项目介绍

你一定遇到过这样的场景：同事发来一份文件，打开却是满屏 `鏂囧瓧` 或 `æ–‡å—`；日志里混着 `Ã©` 和 `Ð`；一个老项目的几百个源文件，谁也说不清哪些是 GBK、哪些是 UTF-8。

**CharsetSeer** 就是为了解决这件事而生的。它是一个**纯 Python 标准库实现**的字符编码检测与乱码修复引擎：

- 🧭 **判得准** —— 不只问"能不能解码"，还追问"解出来像不像人话"
- 🩹 **修得回** —— 自动推断当初误用了哪个编码，把乱码还原成原文
- 📦 **装得上** —— 零第三方依赖，一个 `pip install` 就能用，内网、离线、CI 全都没问题
- 🔒 **靠得住** —— 不联网、不上传、不落日志，你的文件内容不会离开本机

### 解决的痛点

| 痛点 | 传统做法 | CharsetSeer |
| :--- | :--- | :--- |
| 打开就是乱码 | 手动在编辑器里一个个试编码 | 一键判定 + 一键修复，还给出置信度 |
| 老项目编码混杂 | 写脚本 `try/except` 硬猜 | 批量扫描目录，输出编码分布表 |
| 批量转码怕改坏 | 直接覆盖，坏了没法回溯 | `--dry-run` 预演 + `--backup` 备份 |
| 依赖太重装不上 | `chardet` 等包引入额外依赖 | **零依赖**，标准库即可运行 |
| 内网／离线环境 | 需要下载模型或词库 | 完全离线，所有码表运行时推导 |

### 自研差异化亮点

市面上已有 `chardet`、`charset-normalizer` 等优秀方案，CharsetSeer 的差异在于**三条自研判据**与**修复闭环**：

1. **🎯 中文超高频字判据** —— 真实中文的前 900 个高频字能覆盖日常文本的八成以上，而"用错误编码解码"等价于把字节**随机**映射到汉字，落在高频字里的概率很低。这条判据能把"真中文"与"看起来像中文的乱码"干净地切开。
2. **🧬 主导文字一致性检查** —— 一个自称俄语的编码如果只解出零星几个西里尔字母、其余全是 ASCII，它几乎肯定是把西欧重音字母误读成了西里尔。这条规则专治"零星重音字符引发的误判"。
3. **🌐 UTF-8 动态语言推断** —— UTF-8 是通用容器，可以装中文、俄文、阿拉伯文。给它固定一种语言归属，它解出的文字就拿不到契合度加成，反而会被"碰巧解出自己目标文字"的错误编码压过去。CharsetSeer 先解码、再判断里面装的到底是什么语言，然后按该语言打分。
4. **♻️ 修复闭环** —— 检测和修复共用同一套语言学证据，修复时还会用**语言中立的自然度评分**比较候选结果，避免"越修越糟"。

### 灵感来源

感谢 `chardet`、`charset-normalizer`、`file` 等前辈工具在编码识别领域的长期积累。CharsetSeer 参考了它们**解决的问题**（而非代码），在中文／CJK 场景的准确性、零依赖可移植性、以及乱码可逆修复这三个方向上做了独立的实现与优化。

---

## ✨ 核心特性

### 🔤 编码检测

- 🎯 **覆盖 17 种候选编码**：UTF-8/16/32、GB18030（兼容 GBK/GB2312）、Big5、Shift_JIS、EUC-JP、EUC-KR、KOI8-R、CP1250-1256、ISO-8859-7、Latin-1
- 📊 **输出置信度**：不只是给个答案，还告诉你这个答案有多可信（0.00 ~ 1.00）
- 🔍 **可解释**：`--explain` 输出全部候选编码的打分明细，包括字符类别分布与汉字熟悉度
- ⚡ **大文件友好**：默认只取前 256 KB 采样，几 GB 的日志也能秒出结果
- 🏷️ **语言归属**：顺带推测文本语言（简体中文／繁体中文／日文／韩文／俄文／希腊文／阿拉伯文等）

### 🩹 乱码修复

- 🔁 **自动推断误用编码**：枚举 (误用编码, 真实编码) 组合，用语言学证据挑最优解
- 🔄 **多轮修复**：处理被反复错误转码的文本（最多 3 轮）
- 🛡️ **不会乱改**：文本本身正常时返回"未修改"，绝不猜测式改写
- 📈 **乱码可能性评估**：`mojibake_likelihood()` 给出 0.00 ~ 1.00 的乱码概率
- 🧪 **单字节无损原则**：只在字节未丢失时修复；遇到 U+FFFD 等不可逆情况会明确告知

### 🔧 转码与 BOM

- 🔄 **批量转码**：单文件或整个目录，一次性统一到目标编码
- 🧷 **BOM 三种策略**：`keep`（保留）／`add`（添加）／`remove`（移除）
- 💾 **安全写盘**：`--backup` 生成 `.bak` 备份，`--dry-run` 只预演不落盘
- 🧯 **容错可控**：`--on-error` 指定 `strict`／`replace`／`ignore` 处理策略

### 📦 工程化

- 🪶 **零第三方依赖**：仅用 Python 标准库
- 🖥️ **全平台**：Windows / macOS / Linux，Python 3.8+
- 🧪 **101 项单元测试**：覆盖常规样本、短文本、边界输入与 CLI 全流程
- 📤 **多种输出格式**：`text`（对齐表格）／`json`（程序消费）／`csv`（表格软件）
- 🐍 **CLI + 库双用**：命令行即用，也可 `import charsetseer` 二次开发
- 📐 **类型提示齐备**：随包附带 `py.typed`

---

## 🚀 快速开始

### 📋 环境要求

| 项目 | 要求 |
| :--- | :--- |
| Python | **3.8 及以上** |
| 操作系统 | Windows / macOS / Linux（纯 Python，无平台相关代码） |
| 第三方依赖 | **无** |
| 网络 | **不需要**（完全离线运行） |

### 📥 安装

```bash
# 方式一：从 PyPI 安装（推荐）
pip install charsetseer

# 方式二：从源码安装
git clone https://github.com/gitstq/CharsetSeer.git
cd CharsetSeer
pip install -e .

# 方式三：不安装，直接用（克隆后设置 PYTHONPATH）
export PYTHONPATH=$(pwd)
python3 -m charsetseer --help
```

### ✅ 验证安装

```bash
charsetseer --version
# charsetseer 1.0.0

charsetseer codecs
```

### 🎯 三分钟上手

```bash
# 1️⃣ 检测单个文件的编码
charsetseer detect README.md

# 2️⃣ 看看它为什么这么判断（输出全部候选打分）
charsetseer detect --explain mystery.txt

# 3️⃣ 修复一段乱码
charsetseer fix 'ä¸­æå­ç¼ç æ£æµå·¥å·'
# ✨ 修复后：中文编码检测工具

# 4️⃣ 扫描整个项目，看看编码分布
charsetseer scan ./src --summary

# 5️⃣ 批量转成 UTF-8（先预演，确认无误再执行）
charsetseer convert ./src --to utf-8 --dry-run
charsetseer convert ./src --to utf-8 --backup
```

### 🐍 作为库使用

```python
from charsetseer import detect, detect_file, repair, convert_file

# 检测字节串
result = detect("中文编码检测工具".encode("gb18030"))
print(result.encoding)     # gb18030
print(result.confidence)   # 0.93
print(result.language)     # zh-hans

# 检测文件
detection, candidates = detect_file("data.csv", explain=True)

# 修复乱码
broken = "中文编码检测工具".encode("utf-8").decode("latin-1")  # 模拟误读
fixed = repair(broken)
print(fixed.repaired)       # 中文编码检测工具
print(fixed.wrong_encoding) # latin-1
print(fixed.true_encoding)  # utf-8

# 转码（dry_run 先预演）
convert_file("legacy.txt", "utf-8", dry_run=True)
convert_file("legacy.txt", "utf-8", backup=True)
```

---

## 📖 详细使用指南

### 🔍 `detect` —— 检测编码

```bash
charsetseer detect [PATH...] [--explain] [--format text|json] [--preview N]
```

| 参数 | 说明 |
| :--- | :--- |
| `PATH...` | 文件路径；**省略或使用 `-` 则读取标准输入** |
| `--explain` | 输出全部候选编码的打分明细 |
| `--format` | `text`（默认）或 `json` |
| `--preview` | 文本预览长度，默认 200 |

```bash
# 单文件
charsetseer detect data.csv

# 多文件
charsetseer detect a.txt b.txt c.txt

# 管道输入
curl -s https://example.com/page.html | charsetseer detect -

# JSON 输出，便于脚本消费
charsetseer detect --format json data.csv

# 查看打分明细
charsetseer detect --explain mystery.txt
```

<details>
<summary>📄 点击展开：<code>--explain</code> 输出示例</summary>

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

> 「汉字熟悉度」指解码出的汉字落在该编码常用字库中的比例。
> 熟悉度低 = 解出来的是罕用字 = 大概率是乱码。

</details>

### 📂 `scan` —— 批量扫描目录

```bash
charsetseer scan DIR [--include GLOB] [--exclude GLOB] [--max-size N]
                     [--limit N] [--summary] [--format text|json|csv]
```

| 参数 | 说明 |
| :--- | :--- |
| `--include` | 只扫描匹配的文件名，**可重复指定** |
| `--exclude` | 排除匹配的文件名，可重复指定 |
| `--max-size` | 跳过超过该体积的文件，默认 32 MB |
| `--limit` | 最多扫描多少个文件 |
| `--summary` | 额外输出编码分布汇总 |
| `--format` | `text`（默认）／`json`／`csv` |

```bash
# 扫描整个项目
charsetseer scan ./src

# 只看 Python 文件，并统计编码分布
charsetseer scan ./src --include '*.py' --summary

# 导出 CSV，用 Excel 打开分析
charsetseer scan ./src --format csv > encodings.csv

# 排除测试目录
charsetseer scan . --exclude 'test_*' --exclude '*.min.js'
```

> 💡 **自动跳过**：`.git`、`node_modules`、`__pycache__` 等目录，以及
> 图片／音视频／压缩包／PDF 等二进制扩展名（`--max-size` 之外的一层保护）。

<details>
<summary>📄 点击展开：<code>scan --summary</code> 输出示例</summary>

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

### 🩹 `fix` —— 修复乱码

```bash
charsetseer fix [TEXT] [--file PATH] [--in-place] [--aggressive] [--format text|json]
```

| 参数 | 说明 |
| :--- | :--- |
| `TEXT` | 待修复文本；**省略则读取标准输入** |
| `--file` | 从文件读取待修复文本 |
| `--in-place` | 配合 `--file`，把修复结果写回文件 |
| `--aggressive` | 提升不明显时仍强制尝试（结果供人工确认） |
| `--format` | `text`（默认）或 `json` |

```bash
# 直接修复一段文本
charsetseer fix 'ä¸­æå­'

# 从管道读入
cat broken.txt | charsetseer fix

# 修复文件并写回
charsetseer fix --file broken.txt --in-place

# JSON 输出
charsetseer fix 'æå­åãæ¤åº' --format json
```

> ⚠️ **重要：并非所有乱码都能修复。**
> 如果当初误读时产生了 `U+FFFD`（替换字符），字节信息已经**不可逆丢失**，
> CharsetSeer 会明确告知"未发现可信的修复方案"，而不是给你一个似是而非的结果。

### 🔄 `convert` —— 批量转码

```bash
charsetseer convert PATH... --to ENC [--from ENC] [--bom keep|add|remove]
                            [--backup] [--dry-run] [--on-error strict|replace|ignore]
                            [--include GLOB] [--exclude GLOB]
```

| 参数 | 说明 |
| :--- | :--- |
| `--to` | **必填**，目标编码 |
| `--from` | 源编码；省略则自动检测 |
| `--bom` | BOM 策略：`keep`（默认）／`add`／`remove` |
| `--backup` | 写入前生成 `.bak` 备份 |
| `--dry-run` | 只报告将要发生的变更，**不写盘** |
| `--on-error` | 编解码失败处理策略，默认 `replace` |

```bash
# ⚠️ 强烈建议：先预演
charsetseer convert ./docs --to utf-8 --dry-run

# 确认无误后再执行，并保留备份
charsetseer convert ./docs --to utf-8 --backup

# 转码并统一添加 BOM（适配某些 Windows 工具链）
charsetseer convert ./docs --to utf-8 --bom add

# 移除 BOM（适配 Unix 工具链 / 避免 BOM 混入文件内容）
charsetseer convert ./docs --to utf-8 --bom remove

# 明确指定源编码，跳过自动检测
charsetseer convert legacy.txt --from gbk --to utf-8
```

### 🏷️ `bom` —— BOM 检测

```bash
charsetseer bom file1.txt file2.txt [--format json]
```

### 📜 `codecs` —— 查看支持的编码

```bash
charsetseer codecs
```

### 🐍 Python API 全览

```python
from charsetseer import (
    # —— 检测 ——
    detect, detect_bytes, detect_file, guess_language,
    # —— 乱码修复 ——
    repair, repair_bytes, mojibake_likelihood, looks_like_mojibake, naturalness,
    # —— 转码 ——
    convert_file, resolve_encoding, has_bom, strip_bom,
    # —— 扫描 ——
    scan_directory, scan_file, summarize,
)

# ① 检测字节串，返回 Detection 对象
result = detect(raw_bytes)
result.encoding      # 'gb18030'
result.confidence    # 0.93
result.language      # 'zh-hans'
result.has_bom       # False
result.byte_length   # 1024
result.text_preview  # '中文编码检测工具...'

# ② 带候选明细
detection, candidates = detect_bytes(raw, explain=True)
for c in sorted(candidates, key=lambda x: -x.score):
    print(c.encoding, c.score, c.decodable, c.hanzi_familiarity)

# ③ 修复乱码，返回 RepairResult
fixed = repair(broken_text)
fixed.ok              # True
fixed.repaired        # '中文编码检测工具'
fixed.wrong_encoding  # 'latin-1'
fixed.true_encoding   # 'utf-8'
fixed.confidence      # 0.98
fixed.steps           # ['第 1 轮：以 latin-1 重新编码 -> 以 utf-8 解码...']

# ④ 判断是否像乱码
looks_like_mojibake("ä¸­æå­")    # True
mojibake_likelihood("正常中文")     # 0.0

# ⑤ 扫描目录
reports = scan_directory("./src", include=["*.py"])
for r in reports:
    print(r.path, r.encoding, r.confidence)
print(summarize(reports))   # 编码分布统计

# ⑥ 转码（支持 dry_run / backup / BOM 策略）
convert_file("a.txt", "utf-8", dry_run=True)
convert_file("a.txt", "utf-8", backup=True, bom_policy="add")
```

### 🎬 演示

> 📷 **截图 / 演示动图占位**
>
> 此处计划补充：终端 `detect --explain` 输出截图、`fix` 实时修复动图、
> `scan --summary` 编码分布可视化。欢迎 PR 补充素材 🙌

---

## 💡 设计思路与迭代规划

### 🏗️ 架构总览

```
charsetseer/
├── __init__.py      # 公共 API 出口
├── __main__.py      # python -m charsetseer
├── cli.py           # 命令行：detect / scan / fix / convert / bom / codecs
├── detector.py      # 检测引擎：BOM → ASCII → UTF-8 → 多候选语言学打分
├── tables.py        # 编码特征表、字频表、权重与先验（全部运行时推导）
├── mojibake.py      # 乱码检测与多轮修复
├── converter.py     # 转码、BOM 策略、备份与 dry-run
├── scanner.py       # 目录遍历与过滤
├── report.py        # text / json / csv 渲染
└── models.py        # Detection / Candidate / RepairResult / FileReport ...
```

### 🧠 检测流程：证据强度由高到低，逐级收敛

```
   输入字节
      │
      ▼
  ① BOM 指纹 ──────► 命中即定案（置信度 1.00）
      │ 未命中
      ▼
  ② 纯 ASCII ──────► 无歧义（置信度 0.99）
      │ 否
      ▼
  ③ UTF-8 严格验证 ─► UTF-8 有自校验特性，随机字节能合法解码的概率极低
      │
      ▼
  ④ 多候选语言学打分
      ├─ 字节结构快筛（EUC 系列次字节必须 ≥ 0xA1）
      ├─ 严格解码（失败即淘汰）
      ├─ 字符类别加权（汉字 / 假名 / 西里尔 / 拉丁 ...）
      ├─ 🧬 主导文字一致性检查（零星目标文字 → 稀疏惩罚）
      ├─ 🎯 中文超高频字判据（真中文 vs 乱码汉字）
      ├─ 俄语字母频率判据（区分 cp1251 / koi8-r）
      ├─ 专属字符判据（cp1254 的 Ğ/ğ/İ/ı/Ş/ş 等）
      └─ 编码先验（johab 等罕见编码降权）
      │
      ▼
   最高分者胜出 → 由分差与绝对质量推导置信度
```

### 🎯 为什么"高频字"比"常用字"更有效？

这是本项目最关键的一次设计取舍。

最初的实现用"解码出的汉字是否属于 GB2312 一级字库（3755 字）"作为判据，结果**准确率只有 40%**。原因很直接：

> 一级字库有 3755 个字，覆盖面太广 —— 用错误编码解码韩文或俄文时，
> 随机映射出来的汉字**恰好也有很高比例落在这个集合里**，
> 于是"乱码"和"真中文"拿到了一样的熟悉度分数，判别能力被彻底瓦解。

改成**只统计前 900 个超高频字**之后，情况完全不同：真实中文的高频字命中率通常在 60% 以上，而随机解码的命中率不到 15%。两者的分布几乎不重叠，判据一下子变得极其锋利。

一句话总结：**判据的区分度，取决于正负样本在该判据上的分布是否分离，而不是判据本身的"合理性"看起来有多强。**

### ⚖️ 检测打分与修复打分为什么要分开？

这也是一个踩过坑的点。

检测引擎的权重里，汉字权重（2.0）明显高于拉丁字母（0.8）—— 这对**区分编码**是必要的，因为"能解出汉字"正是区分 GBK 与 ASCII 的关键特征。

但修复场景要比较的是**不同语言的正常文本**：`Café déjà vu` 与 `Caf泰 d泰j淌 vu` 谁更正常？如果沿用检测权重，任何"能解出汉字"的错误修复都会系统性地胜出。

因此 `mojibake.py` 另建了一套**语言中立的自然度评分**：只统计"不该出现的字符"（控制符、替换字符、私用区、罕用汉字）与"各自语言的常见字符"，不预设任何语言偏好，再扣除乱码特征分。

### 🗺️ 迭代规划

| 版本 | 计划内容 |
| :--- | :--- |
| **v1.1** | 支持自定义候选编码优先级；为 `scan` 增加并发加速 |
| **v1.2** | 增量式检测（复用上次结论）；`--exclude-dir` 自定义排除目录 |
| **v1.3** | 补充日语／韩语字频表，提升东亚短文本准确率 |
| **v1.4** | 输出 HTML 可视化报告；支持 `--since` 只扫描变更文件 |
| **v2.0** | 可选的统计语言模型插件（仍保持零**强制**依赖） |

### 🤝 社区贡献方向

- 🌍 补充更多语言的字频／字母频率表
- 🧪 补充真实世界的乱码样本（尤其是小语种）
- ⚡ 性能优化（大目录并发扫描）
- 📷 补充文档中的截图与演示动图
- 🌐 更多语言的 README 翻译（日语／韩语／西班牙语）

---

## 📦 打包与部署指南

本项目属于**命令行工具 + Python 库**，无需打包成平台可执行文件。以下为完整的构建、安装与分发流程。

### 🛠️ 构建 wheel 与 sdist

```bash
# 方式一：一键脚本（会先跑测试）
./scripts/build.sh            # Linux / macOS / WSL
scripts\build.bat             # Windows

# 方式二：跳过测试快速构建
./scripts/build.sh --no-test

# 方式三：标准工具链
python3 -m pip install build
python3 -m build --wheel --sdist
```

产物位于 `dist/`：

```
dist/charsetseer-1.0.0-py3-none-any.whl   # 纯 Python 通用 wheel，全平台可用
dist/charsetseer-1.0.0.tar.gz             # 源码分发包
```

> ✅ `py3-none-any` 表示**不依赖任何特定平台或 ABI**，一份 wheel 通吃
> Windows / macOS / Linux。

### 📥 安装产物

```bash
# 安装 wheel
pip install dist/charsetseer-1.0.0-py3-none-any.whl

# 可编辑模式（开发用）
pip install -e .

# 带可选的开发依赖
pip install -e ".[dev]"
```

### 🚀 发布到 PyPI

```bash
# 1. 构建
./scripts/build.sh

# 2. 校验产物
python3 -m twine check dist/*

# 3. 上传到 TestPyPI 演练
python3 -m twine upload --repository testpypi dist/*

# 4. 正式发布
python3 -m twine upload dist/*
```

### 🧪 运行测试

```bash
# 标准库 unittest，无需安装 pytest
python3 -m unittest discover -s tests -v

# 或
make test
```

当前状态：**101 项测试全部通过**，覆盖：

- ✅ 19 种编码的判定正确性（含常规样本与短文本）
- ✅ 边界输入（空文件、单字节、纯二进制、混合内容）
- ✅ 乱码修复的正向与"不应修改"反向用例
- ✅ 转码的 dry-run / backup / BOM 三种策略
- ✅ CLI 全流程与退出码

### 🐳 其他部署形态

```bash
# 单文件免安装运行（适合受限环境）
# 只要把 charsetseer/ 目录复制到目标机器即可
python3 -m charsetseer detect target.txt

# 打包进你自己的项目（零依赖，直接 vendor 也无冲突）
cp -r charsetseer /path/to/your/project/
```

### 🔧 兼容性说明

| 环境 | 状态 |
| :--- | :--- |
| Python 3.8 / 3.9 / 3.10 / 3.11 / 3.12 | ✅ 支持 |
| Windows / macOS / Linux | ✅ 支持 |
| 离线 / 内网环境 | ✅ 支持（无需联网） |
| PyPy | ✅ 理论支持（纯 Python 实现） |

---

## 🤝 贡献指南

欢迎任何形式的贡献！无论是报告 Bug、改进文档，还是提交代码。

### 🐛 提交 Issue

提交前请先搜索现有 Issue 避免重复。报告时请包含：

1. **环境信息**：Python 版本、操作系统、CharsetSeer 版本
2. **复现步骤**：可运行的最小示例
3. **期望行为** vs **实际行为**
4. **样本数据**：如涉及具体文件，请提供能复现的最小字节样本（可用 `xxd` 或 base64 给出）

> 🔒 **隐私提醒**：提交样本前请务必脱敏，不要包含真实业务数据、密钥或个人信息。

### 🔀 提交 Pull Request

```bash
# 1. Fork 本仓库并 clone
git clone https://github.com/<你的用户名>/CharsetSeer.git
cd CharsetSeer

# 2. 创建特性分支
git checkout -b feat/your-feature

# 3. 开发与自测
python3 -m unittest discover -s tests -v

# 4. 提交（遵循 Angular 提交规范）
git commit -m "feat: 新增某某功能"
git commit -m "fix: 修复某某问题"
git commit -m "docs: 更新 README 的某某章节"

# 5. 推送并发起 PR
git push origin feat/your-feature
```

### 📐 提交信息规范

遵循 **Angular 提交规范**：

| 前缀 | 用途 |
| :--- | :--- |
| `feat:` | 新增功能 |
| `fix:` | 修复问题 |
| `docs:` | 文档更新 |
| `refactor:` | 代码重构（不改变外部行为） |
| `perf:` | 性能优化 |
| `test:` | 测试相关 |
| `chore:` | 构建过程或辅助工具变动 |

### ✅ PR 检查清单

- [ ] 代码可通过 `python3 -m unittest discover -s tests -v`（**101 项全部通过**）
- [ ] 新增功能配有对应的单元测试
- [ ] **未引入任何第三方运行时依赖**（这是本项目的核心承诺）
- [ ] 公开函数带有类型提示与中文 docstring
- [ ] 必要时同步更新了 README（含简中／繁中／英文三个版本）
- [ ] 提交信息符合 Angular 规范

### 🎨 代码风格

- 遵循 PEP 8，使用 4 空格缩进
- 公开 API 必须带 docstring（中文优先，便于社区阅读）
- 关键设计取舍请在注释里**写明原因**，而不只是写"做了什么"
- 魔法数字请提取为 `tables.py` 中的具名常量，并附上取值理由

---

## 📄 开源协议说明

本项目基于 **MIT License** 开源，详见 [LICENSE](./LICENSE) 文件。

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

**简而言之：**

- ✅ 允许商业使用、修改、分发、私有化部署
- ✅ 允许用于闭源项目
- ⚠️ 需保留原始版权声明与许可声明
- ❌ 作者不承担任何明示或暗示的担保责任

### 🙏 致谢

- 感谢 `chardet`、`charset-normalizer` 等前辈项目在编码识别领域的探索与启发
- 感谢 Python 标准库 `codecs` 提供的完备编码基础设施 —— 本项目所有码表均由它运行时推导，这也是"零依赖"得以成立的前提
- 感谢所有提交 Issue 与 PR 的社区成员

---

<div align="center">

**如果 CharsetSeer 帮你省下了排查乱码的时间，欢迎 Star ⭐ 支持一下！**

[⬆ 回到顶部](#-charsetseer)

</div>
