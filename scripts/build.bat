@echo off
REM ---------------------------------------------------------------------------
REM CharsetSeer 一键构建脚本（Windows）
REM
REM 用法：
REM   scripts\build.bat            :: 运行测试 + 构建 wheel 与 sdist
REM   scripts\build.bat --no-test  :: 跳过测试，仅构建
REM ---------------------------------------------------------------------------
setlocal enabledelayedexpansion

pushd "%~dp0.."

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] 未找到 python，请先安装 Python 3.8+ 并加入 PATH
    popd & exit /b 1
)

echo [INFO] Python:
python --version

if not "%~1"=="--no-test" (
    echo.
    echo [INFO] 运行单元测试...
    python -m unittest discover -s tests -q
    if errorlevel 1 (
        echo [ERROR] 测试失败，终止构建
        popd & exit /b 1
    )
    echo [OK] 测试通过
)

echo.
echo [INFO] 清理旧构建产物...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
for /d %%d in (*.egg-info) do rmdir /s /q "%%d"

echo.
echo [INFO] 构建 wheel + sdist...
python -m build --wheel --sdist
if errorlevel 1 (
    echo [INFO] 未检测到 build 工具，尝试安装...
    python -m pip install --quiet build
    python -m build --wheel --sdist
    if errorlevel 1 (
        echo [ERROR] 构建失败
        popd & exit /b 1
    )
)

echo.
echo [INFO] 构建产物：
dir /b dist

echo.
echo [OK] 构建完成。安装验证：
echo    python -m pip install dist\charsetseer-*.whl
echo    charsetseer --help

popd
endlocal
