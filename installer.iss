; 录屏王 - Inno Setup 商业级安装包打包脚本

[Setup]
; === 软件基本信息 ===
AppName=录屏王
AppVersion=1.0.0
AppPublisher=你的名字/工作室名称
AppCopyright=Copyright (C) 2024
; 默认安装到 C:\Program Files\录屏王
DefaultDirName={autopf}\录屏王
; 在开始菜单里的文件夹名称
DefaultGroupName=录屏王

; === 极客压缩黑科技 ===
; 开启最高级别的 LZMA2 压缩算法（能把 600M 压到 150M 左右！）
Compression=lzma2/ultra64
SolidCompression=yes

; === 安装包输出设置 ===
; 生成的安装包存放位置（放在当前目录）
OutputDir=.
; 生成的安装包文件名
OutputBaseFilename=录屏王_v1.0_官方安装版
; 安装包自身的图标（复用你的录屏图标）
SetupIconFile=icon.ico

; === 其他体验优化 ===
; 卸载时是否允许删除整个目录
UninstallDisplayIcon={app}\录屏王.exe
; 必须具备管理员权限才能安装
PrivilegesRequired=admin

[Languages]
; 指定安装界面的语言为简体中文（如果你的 Inno 没装中文包，运行时界面可能会降级为英文，但不影响使用）
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
; 提示用户是否创建桌面快捷方式
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; === 核心搬运工 ===
; 1. 先把主程序放进去
Source: "dist\录屏王\录屏王.exe"; DestDir: "{app}"; Flags: ignoreversion
; 2. 把 dist\录屏王 文件夹里的所有依赖 DLL、附带文件夹全部打包进去
Source: "dist\录屏王\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 注意：千万不要在这上面乱改，这段话的意思是“复制 dist\录屏王 里的所有东西到用户的安装目录”

[Icons]
; 生成开始菜单快捷方式
Name: "{group}\录屏王"; Filename: "{app}\录屏王.exe"; IconFilename: "{app}\录屏王.exe"
; 生成桌面快捷方式
Name: "{autodesktop}\录屏王"; Filename: "{app}\录屏王.exe"; Tasks: desktopicon

[Run]
; 安装完成后，弹出一个勾选框问用户“是否立即运行 录屏王”
Filename: "{app}\录屏王.exe"; Description: "{cm:LaunchProgram,录屏王}"; Flags: nowait postinstall skipifsilent