# 录屏大师

一款精美的 Windows 录屏工具，支持全屏录制和区域录制。

## 功能特点

- 🖥 **全屏录制** - 一键录制整个屏幕
- 📐 **区域录制** - 可视化选择录制区域
- ⏯ **录制控制** - 开始/暂停/停止
- ⏱ **实时计时** - 显示录制时长
- 🎨 **精美界面** - 现代化暗色主题设计
- ⌨ **快捷键支持** - F9 开始/停止，F10 暂停/恢复

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 打包为 EXE

双击运行 `build.bat` 或执行：

```bash
pyinstaller build.spec --clean
```

打包后的可执行文件位于 `dist/录屏大师.exe`

## 快捷键

| 按键 | 功能 |
|------|------|
| F9 | 开始/停止录制 |
| F10 | 暂停/恢复录制 |
| ESC | 退出程序（非录制状态） |

## 技术栈

- **GUI**: PySide6 (Qt)
- **屏幕捕获**: mss
- **视频编码**: OpenCV
- **打包**: PyInstaller

## 输出格式

录制的视频保存在 `recordings` 目录，格式为 MP4。

## 系统要求

- Windows 10/11
- Python 3.8+ (仅开发时需要)