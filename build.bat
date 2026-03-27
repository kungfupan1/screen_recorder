@echo off
chcp 65001 >nul
color 0A
echo =========================================
echo       录屏王 - 终极自动化构建流水线
echo =========================================
echo.

echo [1/3] 正在清理旧的构建残留...
if exist "build" rd /s /q "build"
if exist "dist" rd /s /q "dist"
if exist "录屏王_v1.0_官方安装版.exe" del /f /q "录屏王_v1.0_官方安装版.exe"

echo.
echo [2/3] 开始 Python 编译 (PyInstaller)...
echo 这步可能需要几分钟，请耐心等待...
:: 运行你最后跑通的那条终极无敌命令
pyinstaller --noconfirm --onedir --windowed --icon "icon.ico" --collect-all PySide6 --name "录屏王" main.py

:: 检查 Python 编译是否成功
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo.
    echo ❌ 哎呀！Python 打包失败了，请检查上面的报错信息！
    pause
    exit /b
)

echo.
echo [3/3] 开始生成极速压缩安装包 (Inno Setup)...
:: 注意：如果你安装 Inno Setup 时的路径不是默认的，请修改下面的路径
set INNO_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if exist %INNO_PATH% (
    %INNO_PATH% "installer.iss"
) else (
    color 0E
    echo.
    echo ⚠️ 警告：找不到 Inno Setup 编译器！
    echo 请确认是否安装了 Inno Setup，或者手动修改 .bat 里的 Inno 路径。
    pause
    exit /b
)

echo.
echo =========================================
echo   🎉 大功告成！安装包已在当前目录生成！
echo =========================================
pause