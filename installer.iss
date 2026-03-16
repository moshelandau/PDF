; PDF Editor - Inno Setup Installer Script
; Requires Inno Setup: https://jrsoftware.org/isdl.php

[Setup]
AppName=PDF Editor
AppVersion=1.0
AppPublisher=PDF Editor
DefaultDirName={autopf}\PDF Editor
DefaultGroupName=PDF Editor
OutputDir=installer_output
OutputBaseFilename=PDFEditor_Setup
Compression=lzma2
SolidCompression=yes
SetupIconFile=
UninstallDisplayName=PDF Editor
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
; Main application
Source: "dist\PDFEditor.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcuts
Name: "{group}\PDF Editor"; Filename: "{app}\PDFEditor.exe"
Name: "{group}\Uninstall PDF Editor"; Filename: "{uninstallexe}"
; Desktop shortcut
Name: "{autodesktop}\PDF Editor"; Filename: "{app}\PDFEditor.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checked

[Run]
Filename: "{app}\PDFEditor.exe"; Description: "Launch PDF Editor"; Flags: nowait postinstall skipifsilent
