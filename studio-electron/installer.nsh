; TajikLang Studio — Windows integration for the Electron NSIS installer.
; A student gets the same two entry points expected from a real language:
; double-clicking a .tj file opens Studio; `tajik file.tj` runs from a shell.

!include "LogicLib.nsh"
!include "WinMessages.nsh"

!define SHCNE_ASSOCCHANGED 0x08000000
!define SHCNF_IDLIST 0x0000

!macro customInstall
  WriteRegStr HKCU "Software\Classes\.tj" "" "TajikLang.Program"
  WriteRegStr HKCU "Software\Classes\.tj" "Content Type" "text/x-tajiklang"
  WriteRegStr HKCU "Software\Classes\TajikLang.Program" "" "Барномаи TajikLang"
  WriteRegStr HKCU "Software\Classes\TajikLang.Program" "FriendlyTypeName" "Барномаи TajikLang (.tj)"
  WriteRegStr HKCU "Software\Classes\TajikLang.Program\DefaultIcon" "" "$INSTDIR\TajikLang Studio.exe,0"
  WriteRegStr HKCU "Software\Classes\TajikLang.Program\shell\open\command" "" '"$INSTDIR\TajikLang Studio.exe" "%1"'
  WriteRegStr HKCU "Software\Classes\TajikLang.Program\shell\run" "" "Иҷро дар терминали TajikLang"
  WriteRegStr HKCU "Software\Classes\TajikLang.Program\shell\run\command" "" '"$SYSDIR\cmd.exe" /d /k ""$INSTDIR\tajik.cmd" "%1""'

  ; A visible command wrapper means `tajik` works in both Command Prompt and
  ; PowerShell, without students finding the private resources/runtime folder.
  FileOpen $2 "$INSTDIR\tajik.cmd" w
  FileWrite $2 "@echo off$\r$\n"
  FileWrite $2 '"$INSTDIR\resources\runtime\tajik.exe" %*$\r$\n'
  FileClose $2

  ReadRegStr $0 HKCU "Environment" "Path"
  StrCpy $1 "$INSTDIR"
  ${IfThen} $0 == "" ${|} StrCpy $0 $1 ${|}
  ${IfThen} $0 != "" ${|} StrCpy $0 "$1;$0" ${|}
  WriteRegExpandStr HKCU "Environment" "Path" "$0"
  SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=5000
  System::Call 'shell32::SHChangeNotify(i ${SHCNE_ASSOCCHANGED}, i ${SHCNF_IDLIST}, p0, p0)'
!macroend

!macro customUnInstall
  DeleteRegKey HKCU "Software\Classes\TajikLang.Program"
  DeleteRegValue HKCU "Software\Classes\.tj" ""
  System::Call 'shell32::SHChangeNotify(i ${SHCNE_ASSOCCHANGED}, i ${SHCNF_IDLIST}, p0, p0)'
  ; The PATH entry is deliberately retained on uninstall only when other
  ; TajikLang runtimes may still be installed; repair/upgrades remain safe.
!macroend
