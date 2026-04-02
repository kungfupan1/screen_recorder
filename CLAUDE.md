# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

录屏王 (Screen Recorder King) - A Windows screen recording application with a modern dark-themed UI. Supports fullscreen recording, region selection, and multi-monitor recording.

## Commands

```bash
# Run the application
python main.py

# Install dependencies
pip install -r requirements.txt

# Build EXE (PyInstaller only - produces dist/录屏王/ folder)
pyinstaller 录屏王.spec --clean --noconfirm

# Build full installer (PyInstaller + Inno Setup)
build.bat
# Requires Inno Setup 6 installed at C:\Program Files (x86)\Inno Setup 6\
# Produces 录屏王_v1.0_官方安装版.exe in project root

# Test coordinate system (debug utility)
python test_coords.py
```

## Architecture

```
screen_recorder/
├── main.py              # Entry point, DPI setup, Qt plugin path
├── test_coords.py       # Debug utility for coordinate system verification
├── recorder/            # Core recording functionality
│   ├── controller.py    # RecordController + ScreenRecorder classes
│   └── area_selector.py # Fullscreen overlay for region selection (冻结桌面方案)
├── ui/                  # PySide6 UI components
│   ├── main_window.py   # MainWindow, VideoCard, MonitorSelector
│   ├── widgets.py       # Custom Qt widgets (RecordButton, ModeButton, etc.)
│   └── styles.py        # Color scheme and stylesheet definitions
├── utils/
│   └── config.py        # Configuration management
├── 录屏王.spec           # PyInstaller spec file
├── build.bat            # Full build pipeline (PyInstaller + Inno Setup)
├── installer.iss        # Inno Setup script for Windows installer
└── icon.ico             # Application icon
```

## Key Technical Details

### Threading Model (Critical)
- `ScreenRecorder` runs **two threads** per recording target: `_capture_worker` and `_write_worker`
- **mss objects CANNOT be shared across threads** - each capture thread creates its own `mss.mss()` instance using `with mss.mss() as sct:`
- Frames are passed between threads via a `Queue(maxsize=120)` to prevent memory overflow
- The capture thread uses time-based frame synchronization to maintain accurate FPS:
  - Uses `time.perf_counter()` to track elapsed time
  - Calculates `target_count = int((current_time - start_time) * fps) + 1`
  - Adds duplicate frames if needed to compensate for timing drift (补帧逻辑)
  - Sleep duration calculated to hit exact next frame time

### DPI/Coordinate System
- `main.py` calls `ctypes.windll.shcore.SetProcessDpiAwareness(2)` for physical pixel coordinates
- `area_selector.py` uses a "冻结桌面" approach: captures entire virtual desktop screenshot first, then overlays a fullscreen selection UI on top of the frozen image
- Coordinates from the selector are **absolute physical coordinates** relative to the virtual desktop (`monitors[0]`)
- This approach ensures 100% coordinate accuracy across multi-monitor setups with different DPI scalings

### Video Encoding
- Uses OpenCV `cv2.VideoWriter` with `mp4v` codec
- Resolution must be **even numbers** (width/height are adjusted to even if odd)
- Default FPS: 30

### Multi-Monitor Support
- `RecordController.get_monitors()` returns `sct.monitors[1:]` (actual displays, index 0 is virtual desktop)
- Each selected monitor gets its own `ScreenRecorder` instance with independent capture/write threads
- Recording multiple monitors produces multiple video files

### UI/Controller Communication
- `RecordController` uses callback pattern: `on_status_changed` and `on_recording_complete` callbacks
- `MainWindow` connects these callbacks to update UI state (status indicator, time display, video list)
- Video thumbnails are generated asynchronously via `QTimer.singleShot()` after `VideoCard` creation

## Common Pitfalls

1. **Never share mss instance across threads** - causes `_thread._local object has no attribute 'srcdc'` error
2. **Frame rate drift** - use `time.perf_counter()` based timing, not simple `sleep(1/fps)`
3. **Odd dimensions** - OpenCV requires even width/height, always adjust
4. **Qt plugin path** - must be set before QApplication creation for packaged exe
5. **DPI scaling** - Windows scaling causes coordinate mismatch; use physical coordinates

## Output Location

Videos are saved to `~/Videos/录屏王/` (user's Videos folder)

## Keyboard Shortcuts

Handled in `ui/main_window.py` via `keyPressEvent`:
- **F9**: Toggle recording (start/stop)
- **F10**: Pause/resume recording
- **ESC**: Exit application (only when not recording)