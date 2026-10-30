#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# CharsetSeer 一键构建脚本（Linux / macOS / WSL）
#
# 用法：
#   ./scripts/build.sh            # 运行测试 + 构建 wheel 与 sdist
#   ./scripts/build.sh --no-test  # 跳过测试，仅构建
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"

echo "🐍 Python: $($PYTHON --version 2>&1)"

# ---- 1. 单元测试 ----------------------------------------------------------
if [[ "${1:-}" != "--no-test" ]]; then
    echo ""
    echo "🧪 运行单元测试..."
    "$PYTHON" -m unittest discover -s tests -q
    echo "✅ 测试通过"
fi

# ---- 2. 清理旧产物 --------------------------------------------------------
echo ""
echo "🧹 清理旧构建产物..."
rm -rf build dist ./*.egg-info

# ---- 3. 构建 --------------------------------------------------------------
echo ""
echo "📦 构建 wheel + sdist..."
if "$PYTHON" -m build --wheel --sdist 2>/dev/null; then
    :
else
    # 未安装 build 时回退到 setuptools 直连方式
    echo "   （未检测到 build 工具，回退到 setuptools）"
    "$PYTHON" -m pip install --quiet build
    "$PYTHON" -m build --wheel --sdist
fi

# ---- 4. 产物校验 ----------------------------------------------------------
echo ""
echo "🔍 构建产物："
ls -lh dist/ 2>/dev/null || { echo "❌ 未生成产物"; exit 1; }

echo ""
echo "🎉 构建完成。安装验证："
echo "   python3 -m pip install dist/charsetseer-*.whl"
echo "   charsetseer --help"
