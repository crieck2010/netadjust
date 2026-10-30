; Inno Setup script for NetAdjust (build dist\NetAdjust.exe first with build_exe.bat)
#define AppName "NetAdjust"
#define AppVersion "0.1.0"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputBaseFilename=NetAdjust-Setup-{#AppVersion}
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\NetAdjust.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\NetAdjust.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\NetAdjust.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"
