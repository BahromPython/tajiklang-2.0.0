; TajikLang Windows installer — compiled with Inno Setup 6.
; Students download one .exe, click Install, and get a desktop shortcut.

#ifndef AppVersion
  #define AppVersion "2.1.5"
#endif
#ifndef AppArch
  #define AppArch "x64"
#endif

[Setup]
AppId={{79F23E1A-A587-4F72-8B1F-8D135097427C}
AppName=TajikLang
AppVersion={#AppVersion}
AppPublisher=TajikLang
AppPublisherURL=https://github.com/BahromPython/tajiklang-2.0.0
DefaultDirName={localappdata}\Programs\TajikLang
DefaultGroupName=TajikLang
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=TajikLang-Setup-Windows-{#AppArch}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Studio\TajikLang.exe

#if AppArch == "x64"
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
#endif

[Files]
Source: "dist\TajikLang\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\TajikLang Studio"; Filename: "{app}\Studio\TajikLang.exe"; WorkingDir: "{app}\Studio"; Comment: "Муҳаррири TajikLang"
Name: "{autodesktop}\TajikLang Studio"; Filename: "{app}\Studio\TajikLang.exe"; WorkingDir: "{app}\Studio"; Comment: "Муҳаррири TajikLang"

[Registry]
Root: HKCU; Subkey: "Software\Classes\.tj"; ValueType: string; ValueName: ""; ValueData: "TajikLang.File"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\TajikLang.File"; ValueType: string; ValueName: ""; ValueData: "Барномаи TajikLang"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\TajikLang.File\shell\open\command"; ValueType: string; ValueName: ""; ValueData: "&quot;{app}\tajik.exe&quot; &quot;%1&quot;"
Root: HKCU; Subkey: "Software\Classes\TajikLang.File\shell\edit\command"; ValueType: string; ValueName: ""; ValueData: "&quot;{app}\tajik.exe&quot; муҳаррир &quot;%1&quot;"

[Run]
Filename: "{app}\Studio\TajikLang.exe"; Description: "Муҳаррири TajikLang-ро кушоед"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
