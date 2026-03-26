# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

录屏大师 (Screen Recorder Master) - A Windows screen recording application with a modern dark-themed UI. Supports fullscreen recording, region selection, and multi-monitor recording.

## Commands

```bash
# Run the application
python main.py

# Install dependencies
pip install -r requirements.txt

# Build EXE
pyinstaller build.spec --clean --noconfirm
# Or use the batch script
build.bat

# Test coordinate system (debug utility)
python test_coords.py
```

## Architecture

```
screen_recorder/
├── main.py              # Entry point, DPI setup, Qt plugin path
├── recorder/            # Core recording functionality
│   ├── controller.py    # RecordController + ScreenRecorder classes
│   ├── area_selector.py # Fullscreen overlay for region selection
│   ├── screen_capture.py# Legacy capture utility (not used by controller)
│   └── video_writer.py  # Legacy video writer (not used by controller)
├── ui/                  # PySide6 UI components
│   ├── main_window.py   # Main application window
│   ├── widgets.py       # Custom Qt widgets (RecordButton, ModeButton, etc.)
│   └── styles.py        # Color scheme and stylesheet definitions
└── utils/
    └── config.py        # Configuration management
```

## Key Technical Details

### Threading Model (Critical)
- `ScreenRecorder` runs **two threads** per recording target: `_capture_worker` and `_write_worker`
- **mss objects CANNOT be shared across threads** - each capture thread creates its own `mss.mss()` instance using `with mss.mss() as sct:`
- Frames are passed between threads via a `Queue(maxsize=120)` to prevent memory overflow
- The capture thread uses time-based frame synchronization to maintain accurate FPS

### DPI/Coordinate System
- `main.py` calls `ctypes.windll.shcore.SetProcessDpiAwareness(2)` for physical pixel coordinates
- `area_selector.py` captures a frozen screenshot of the entire virtual desktop using mss, then overlays a selection UI
- Coordinates from the selector are **absolute physical coordinates** relative to the virtual desktop (`monitors[0]`)

### Video Encoding
- Uses OpenCV `cv2.VideoWriter` with `mp4v` codec
- Resolution must be **even numbers** (width/height are adjusted to even if odd)
- Default FPS: 30

### Multi-Monitor Support
- `RecordController.get_monitors()` returns `sct.monitors[1:]` (actual displays, index 0 is virtual desktop)
- Each selected monitor gets its own `ScreenRecorder` instance with independent capture/write threads
- Recording multiple monitors produces multiple video files

## Common Pitfalls

1. **Never share mss instance across threads** - causes `_thread._local object has no attribute 'srcdc'` error
2. **Frame rate drift** - use `time.perf_counter()` based timing, not simple `sleep(1/fps)`
3. **Odd dimensions** - OpenCV requires even width/height, always adjust
4. **Qt plugin path** - must be set before QApplication creation for packaged exe
5. **DPI scaling** - Windows scaling causes coordinate mismatch; use physical coordinates

## Output Location

Videos are saved to `~/Videos/录屏大师/` (user's Videos folder)