# 🤝 贡献指南 / Contributing

感谢你愿意为 CharsetSeer 贡献力量！本文档说明如何参与开发。

## 🚀 开始之前

```bash
git clone https://github.com/gitstq/CharsetSeer.git
cd CharsetSeer
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

无需安装 pytest —— 测试基于 Python 标准库的 `unittest`。

## 🎯 核心原则（请务必遵守）

1. **零第三方运行时依赖** —— 这是本项目的立身之本。任何 PR 都不得引入
   运行时第三方包。开发与打包依赖请放在 `requirements-dev.txt` 或
   `pyproject.toml` 的 `[project.optional-dependencies]` 中。

2. **完全离线** —— 不得发起任何网络请求、不加载外部模型或数据文件。
   所有码表必须由 Python 标准库 `codecs` 在运行时推导。

3. **不猜测式改写** —— 修复类功能必须在证据充分时才生效；
   证据不足时返回"未修改"，而不是给一个似是而非的结果。

## 📐 提交规范

遵循 **Angular 提交规范**：

| 前缀 | 用途 |
| :--- | :--- |
| `feat:` | 新增功能 |
| `fix:` | 修复问题 |
| `docs:` | 文档更新 |
| `refactor:` | 代码重构 |
| `perf:` | 性能优化 |
| `test:` | 测试相关 |
| `chore:` | 构建与工具 |

示例：

```
feat: 为 scan 增加 --exclude-dir 参数
fix: 修复 utf-8 目标编码下 --bom add 静默失效的问题
docs: 补充 README 的多轮修复说明
```

## ✅ PR 检查清单

- [ ] 全部 101 项测试通过
- [ ] 新增功能配套单元测试
- [ ] 未引入第三方运行时依赖
- [ ] 公开 API 带类型提示与 docstring
- [ ] 必要时同步更新三语 README（简中 / 繁中 / English）
- [ ] 关键设计取舍在注释中写明**原因**

## 🎨 代码风格

- PEP 8，4 空格缩进
- 公开 API 必须带 docstring
- 魔法数字提取为 `tables.py` 中的具名常量，并说明取值理由
- 注释解释「为什么」而非「做了什么」

## 🐛 报告问题

请包含：环境信息（Python 版本 / 操作系统 / CharsetSeer 版本）、
最小复现示例、期望与实际行为。

> 🔒 提交样本前请脱敏，不要包含真实业务数据、密钥或个人信息。

## 🌍 翻译

欢迎补充日语、韩语、西班牙语等更多语言版本的 README。
请确保是**母语级表达**，而非机器翻译 —— 项目对文档质量的要求与代码一致。
