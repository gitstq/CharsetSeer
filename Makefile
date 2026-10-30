# CharsetSeer —— 常用任务入口
#
#   make test     运行单元测试
#   make build    构建 wheel + sdist
#   make install  以可编辑模式安装到当前环境
#   make demo     快速体验（检测 / 修复 / 扫描）
#   make clean    清理构建产物
#
# Windows 用户请改用 scripts\build.bat。

PYTHON ?= python3

.PHONY: help test build install demo clean

help:
	@echo "CharsetSeer 可用目标："
	@echo "  make test     运行单元测试"
	@echo "  make build    构建 wheel + sdist"
	@echo "  make install  以可编辑模式安装"
	@echo "  make demo     快速体验"
	@echo "  make clean    清理构建产物"

test:
	$(PYTHON) -m unittest discover -s tests -v

build:
	./scripts/build.sh

install:
	$(PYTHON) -m pip install -e .

demo:
	@echo "=== 1) 检测一段 GBK 字节 ==="
	@$(PYTHON) -c "import charsetseer;print(charsetseer.detect('中文编码检测工具'.encode('gb18030')))"
	@echo ""
	@echo "=== 2) 修复乱码 ==="
	@$(PYTHON) -c "import charsetseer;print(charsetseer.repair('中文编码检测工具'.encode('utf-8').decode('latin-1')).repaired)"
	@echo ""
	@echo "=== 3) 扫描当前目录 ==="
	@PYTHONPATH=. $(PYTHON) -m charsetseer scan . --include '*.py'

clean:
	rm -rf build dist ./*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.py[co]' -delete 2>/dev/null || true
