# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置

使用方法:
    pyinstaller build.spec --clean --noconfirm
"""

import os
import glob
import PySide6

block_cipher = None

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(SPEC))

# PySide6 插件路径
pyside_dir = os.path.dirname(PySide6.__file__)
platforms_path = os.path.join(pyside_dir, 'plugins', 'platforms')

# 图标路径
icon_path = os.path.join(current_dir, 'icon.ico')

# 收集 platforms 目录下的所有 DLL 文件
platforms_files = glob.glob(os.path.join(platforms_path, '*.dll'))

# 构建 datas 列表
datas_list = []
for dll in platforms_files:
    datas_list.append((dll, 'PySide6/plugins/platforms'))

print(f"Adding {len(datas_list)} platform plugin files:")
for d in datas_list:
    print(f"  {d[0]} -> {d[1]}")

a = Analysis(
    ['main.py'],
    pathex=[current_dir],
    binaries=[],
    datas=datas_list,
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'mss',
        'cv2',
        'numpy',
        'ui',
        'ui.main_window',
        'ui.widgets',
        'ui.styles',
        'recorder',
        'recorder.screen_capture',
        'recorder.video_writer',
        'recorder.controller',
        'recorder.area_selector',
        'utils',
        'utils.config',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='录屏王',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)