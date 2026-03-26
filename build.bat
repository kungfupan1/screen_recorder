@echo off
chcp 65001 >nul
echo ========================================
echo     录屏大师 - 打包脚本
echo ========================================
echo.

echo [1/3] 检查依赖...
pip show pyinstaller >nul 2>&1 || (
    echo 正在安装 PyInstaller...
    pip install pyinstaller
)

echo.
echo [2/3] 清理旧文件...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo [3/3] 开始打包...
echo 这可能需要几分钟时间，请耐心等待...
echo.

pyinstaller build.spec --clean --noconfirm

echo.
if exist "dist\录屏大师.exe" (
    echo ========================================
    echo 打包成功！
    echo ========================================
    echo.
    echo 可执行文件位置: dist\录屏大师.exe
    echo.
    echo 正在打开输出目录...
    explorer dist
) else (
    echo ========================================
    echo 打包失败，请检查错误信息。
    echo ========================================
)

echo.
pause