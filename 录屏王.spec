# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os

datas = [('ffmpeg.exe', '.')]
binaries = []
hiddenimports = []
tmp_ret = collect_all('PySide6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

# Pillow（免费版水印渲染）
hiddenimports += ['PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont']

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# ──── 黑名单过滤：删除确定不用的 Qt 模块，减小打包体积 ────
# 过滤 Analysis 输出（a.binaries / a.datas），在传给 COLLECT 之前拦截

# 零风险排除的 Qt 模块前缀（DLL + .pyd + .pyi）
_BLACKLIST_MODULES = [
    'Qt6WebEngine', 'QtWebEngine',
    'Qt63D', 'Qt3DAnimation', 'Qt3DCore', 'Qt3DExtras', 'Qt3DInput', 'Qt3DLogic', 'Qt3DRender',
    'Qt6Bluetooth', 'QtBluetooth',
    'Qt6Charts', 'QtCharts',
    'Qt6Graphs', 'QtGraphs',
    'Qt6DataVisualization', 'QtDataVisualization',
    'Qt6Designer', 'QtDesigner', 'QtUiTools',
    'Qt6Help', 'QtHelp',
    'Qt6Location', 'QtLocation',
    'Qt6Positioning', 'QtPositioning',
    'Qt6Multimedia', 'QtMultimedia',
    'Qt6Pdf', 'QtPdf',
    'Qt6Sensors', 'QtSensors',
    'Qt6SerialPort', 'QtSerialPort',
    'Qt6Sql', 'QtSql',
    'Qt6Test', 'QtTest',
    'Qt6TextToSpeech', 'QtTextToSpeech',
]

# 零风险排除的 Qt 开发工具 exe
_BLACKLIST_EXES = {
    'assistant.exe', 'balsam.exe', 'balsamui.exe', 'designer.exe',
    'linguist.exe', 'lrelease.exe', 'lupdate.exe',
    'qmlcachegen.exe', 'qmlformat.exe', 'qmlimportscanner.exe',
    'qmlls.exe', 'qmltyperegistrar.exe', 'qsb.exe', 'rcc.exe',
    'svgtoqml.exe', 'uic.exe', 'QtWebEngineProcess.exe',
}

# 零风险排除的 datas 子目录
_BLACKLIST_DATAS_DIRS = {'include', 'typesystems', 'scripts', 'translations'}

# 全部小写加速查找
_blacklist_mod_lower = [m.lower() for m in _BLACKLIST_MODULES]


def _should_remove(name):
    """检查文件名是否属于黑名单模块或开发工具"""
    low = name.lower()
    for mod in _blacklist_mod_lower:
        if low.startswith(mod):
            return True
    if low in _BLACKLIST_EXES:
        return True
    return False


# 过滤 a.binaries
a.binaries = [b for b in a.binaries if not _should_remove(os.path.basename(b[0]))]

# 过滤 a.datas：移除黑名单模块文件 + 排除目录
# a.datas 是 TOC 格式: (dest_name, source_path, type)
def _should_remove_data(entry):
    dest_name = entry[0]  # 目标路径，如 "PySide6/include/xxx.h"
    name = os.path.basename(dest_name)
    if _should_remove(name):
        return True
    # 检查排除目录 (dest_name 形如 "PySide6/include/xxx.h")
    parts = dest_name.replace('\\', '/').split('/')
    if len(parts) >= 2 and parts[0] == 'PySide6' and parts[1] in _BLACKLIST_DATAS_DIRS:
        return True
    return False

a.datas = [d for d in a.datas if not _should_remove_data(d)]

print(f'[spec 过滤] binaries: {len(a.binaries)} 项, datas: {len(a.datas)} 项')


pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='录屏王',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='录屏王',
)
