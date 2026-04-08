# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

录屏王 (Screen Recorder King) - A Windows screen recording application built with PySide6 and qfluentwidgets. Features a modern dark-themed UI with frameless window, fullscreen recording, region selection (freeze-desktop overlay), and multi-monitor recording.

**System requirements**: Windows 10/11, Python 3.8+

**Key dependencies**: PySide6, PySide6-Fluent-Widgets (imported as `qfluentwidgets`), mss (screen capture), opencv-python (video encoding), cryptography (license verification), qrcode (QR code generation), requests (API calls)

**No test suite** — only `test_coords.py` (coordinate debug utility). No unit tests exist.

## Commands

```bash
# Run the application
python main.py

# Install dependencies
pip install -r requirements.txt

# Build EXE (PyInstaller - produces dist/录屏王/ folder)
pyinstaller --noconfirm --onedir --windowed --icon "icon.ico" --collect-all PySide6 --name "录屏王" main.py
# Alternative: use spec file
pyinstaller 录屏王.spec --clean --noconfirm

# Build full installer (PyInstaller + Inno Setup LZMA2 compression)
build.bat
# Requires Inno Setup 6 at C:\Program Files (x86)\Inno Setup 6\
# Produces 录屏王_v1.0_官方安装版.exe in project root

# Test coordinate system (debug utility)
python test_coords.py
```

## Architecture

```
main.py                 # Entry point: DPI awareness (SetProcessDpiAwareness(2)), app bootstrap
recorder/
  controller.py         # RecordController (orchestrator) + ScreenRecorder (per-target worker)
  area_selector.py      # Fullscreen overlay for region selection (冻结桌面方案)
  screen_capture.py     # UNUSED - dead code
  video_writer.py       # UNUSED - dead code
ui/
  main_window.py        # MainWindow, VideoCard, MonitorSelector, BokehBackground - main application UI
  pay_dialog.py         # PayDialog, PlanCard, AgreementDialog, RedeemDialog, BokehBackground (duplicate)
  widgets.py            # Custom widgets: TitleBar, RecordButton, ModeButton, StatusIndicator, TimeDisplay
  styles.py             # Color constants (COLORS dict) + stylesheet templates used by widgets.py
license/
  activation.py         # Entry point: check_activation() + activate_with_code() — startup check + offline verify
  verifier.py           # Ed25519 offline license verification (REC-{Base64URL(78 bytes)} format)
  machine_code.py       # Hardware fingerprint via wmic CPU ProcessorId (SHA-256 → XXXX-XXXX-XXXX-XXXX)
  cache_manager.py      # Local JSON cache at %LOCALAPPDATA%\录屏王\ (license.json, plans_cache.json)
  api_client.py         # JustPay API client (fetch plans, create order, poll order status, verify online)
utils/
  config.py             # sc() DPI scaling function, Config class, DEFAULT_CONFIG, get_resource_path()
```

## Key Technical Details

### DPI Scaling (`sc()` function)

`utils/config.py` defines `_get_dpi_scale()` which reads system DPI via Win32 API, computes `UI_SCALE = max(dpi / 96.0, 1.0)`. The `sc(size)` function scales any pixel value by this factor. **Every UI file** uses `sc()` for all dimensions — fonts, spacing, widget sizes. The app disables Qt's built-in scaling (`QT_AUTO_SCREEN_SCALE_FACTOR=0`, `QT_ENABLE_HIGHDPI_SCALING=0`) and handles it manually via `sc()`.

### Recording Pipeline (controller.py)

`RecordController` manages one or more `ScreenRecorder` instances. Each `ScreenRecorder` runs **two threads**:
- **`_capture_worker`**: Captures frames using `mss` (creates its own `mss.mss()` per thread — see pitfalls), pushes to a `Queue(maxsize=120)`
- **`_write_worker`**: Pulls frames from queue and writes via `cv2.VideoWriter`

Frame synchronization uses `time.perf_counter()`:
- `target_count = int((current_time - start_time) * fps) + 1`
- Duplicate frames added if behind (补帧 logic)
- Sleep calculated to hit exact next frame time

Pause/resume at the `ScreenRecorder` level tracks pause duration to adjust `start_time`, ensuring continuous timeline.

### DPI/Coordinate System

- `main.py` sets `SetProcessDpiAwareness(2)` (per-monitor DPI aware v2) before Qt init
- `QT_AUTO_SCREEN_SCALE_FACTOR=0` and `QT_ENABLE_HIGHDPI_SCALING=0` — Qt scaling disabled, app uses raw physical pixels
- `area_selector.py` captures the full virtual desktop (`monitors[0]`) with mss, then creates a frameless topmost window over it. User draws selection on this frozen screenshot.
- All coordinates are **absolute physical coordinates** relative to the virtual desktop origin

### UI/Controller Communication

- Callback pattern: `RecordController.on_status_changed` and `on_recording_complete` callbacks
- `MainWindow` connects these to update status indicator, time display, and video card list
- **Pause bug**: `_toggle_pause` in MainWindow directly sets `self.recorder.is_paused` flag and stops/starts the display timer, but does NOT call `RecordController.pause()/resume()`. This means the `ScreenRecorder` threads keep capturing frames — only the time display freezes. The controller's `pause()` method would propagate to each `ScreenRecorder.pause()` which sets `_pause_event` to actually stop capture, but this path is never called from the UI.
- Video thumbnails generated asynchronously via `QTimer.singleShot(100, ...)` after VideoCard creation

### Multi-Monitor Support

- `RecordController.get_monitors()` returns `sct.monitors[1:]` (index 0 is virtual desktop)
- Each selected monitor gets its own `ScreenRecorder` instance
- Recording multiple monitors produces separate video files (`recording_screen{idx}_{timestamp}.mp4`)

### Video Encoding

- OpenCV `cv2.VideoWriter` with `mp4v` codec
- Dimensions forced to even numbers (odd dimensions reduced by 1)
- Default FPS: 30, output format: MP4

### UI Framework

- Uses `qfluentwidgets` (from `PySide6-Fluent-Widgets` package) for modern Fluent Design components
- Dark theme set globally via `setTheme(Theme.DARK)` and `setThemeColor("#00d9ff")`
- Frameless window with custom `TitleBar` widget for drag/minimize/close
- Styling is a mix: `ui/styles.py` provides color constants (`COLORS` dict) and stylesheet templates imported by `widgets.py`; `main_window.py` and `pay_dialog.py` add additional inline styles via `setStyleSheet()`
- `BokehBackground` (animated light-spot background) is **duplicated** in both `main_window.py` and `pay_dialog.py` with slightly different parameters — changes to one won't affect the other
- `setTheme(Theme.DARK)` in `PayDialog.__init__()` injects global CSS that can override child widget styling — use object name selectors and explicit `background: transparent` on containers to prevent cascade issues

### Build/Packaging

- PyInstaller with `--collect-all PySide6` bundles all Qt dependencies
- Spec file (`录屏王.spec`) declares `hiddenimports` for license modules, qrcode, and cryptography — needed for PyInstaller to find them
- `console=False` for windowed exe, icon from `icon.ico`
- `build.bat` chains PyInstaller → Inno Setup (LZMA2/ultra64 compression)
- `installer.iss` creates Start Menu shortcut, optional Desktop shortcut, Chinese UI
- Resource loading: `utils/config.py` has `get_resource_path()` that resolves to `sys._MEIPASS` when frozen

## Common Pitfalls

1. **Never share mss instance across threads** — causes `_thread._local object has no attribute 'srcdc'` error. Each `_capture_worker` creates its own `with mss.mss() as sct:`
2. **Frame rate drift** — use `time.perf_counter()` based timing, never simple `sleep(1/fps)`
3. **Odd dimensions** — OpenCV VideoWriter requires even width/height
4. **DPI scaling** — Windows scaling causes coordinate mismatch; the app disables Qt scaling and uses physical coordinates. Always use `sc()` for pixel values in UI code.
5. **Dead code** — `recorder/screen_capture.py` and `recorder/video_writer.py` are unused; keep them out of refactor scope. (`ui/styles.py` IS used by `widgets.py` — do not delete it.)
6. **PyInstaller hidden imports** — license modules (`license.*`), `qrcode`, and `cryptography` must be listed in `hiddenimports` in the spec file or they won't be bundled
7. **Pause doesn't actually pause recording** — see "Pause bug" in UI/Controller Communication section
8. **qfluentwidgets `setTheme(Theme.DARK)` cascading** — calling this injects global CSS that can make child widgets invisible (e.g. black text on black background). Diagnose from the top-level window down; use `background: transparent` on intermediate containers and object-name selectors to override.
9. **BokehBackground duplication** — exists in both `main_window.py` and `pay_dialog.py`. Fixes to one must be manually applied to the other.

## License/Payment System

- **Offline-first verification**: License codes use Ed25519 signatures (format `REC-{Base64URL(78 bytes)}`: version(1) + plan_id(1) + machine_hash(8) + expire_ts(4 BE) + signature(64))
- **Machine binding**: `machine_code.py` generates fingerprint from CPU ProcessorId, stored alongside license in `%LOCALAPPDATA%\录屏王\license.json`
- **Payment flow**: `PayDialog` fetches plans from JustPay API → creates order → shows WeChat QR code → polls order status every 3s → auto-activates on payment
- **Redeem code**: Accessible via "more" (⋯) button in PayDialog title bar → "兑换码激活" menu item, accepts `REC-` prefixed codes directly
- **Gate**: `MainWindow` checks `check_activation()` at startup; unactivated users see PayDialog when clicking record (via `_license_activated` flag)
- **API backend**: `https://payment.winepipeline.com` with `app_code=screen_recorder`

## Output Location

Videos saved to `~/Videos/录屏王/` (user's Videos folder)

## Keyboard Shortcuts

Handled in `ui/main_window.py` via `keyPressEvent`:
- **F9**: Toggle recording (start/stop)
- **F10**: Pause/resume recording
- **ESC**: Exit application (only when not recording)

## Note

`README.md` is outdated — it says "录屏大师" and references `build.spec` (neither match current code). The canonical source for project info is this file.
