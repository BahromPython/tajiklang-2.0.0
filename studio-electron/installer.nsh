; TajikLang Studio — Windows integration for the Electron NSIS installer.
; A student gets the same two entry points expected from a real language:
; double-clicking a .tj file opens Studio; `tajik file.tj` runs from a shell.

!include "LogicLib.nsh"
!include "WinMessages.nsh"

!macro customInstall
  WriteRegStr HKCU "Software\Classes\.tj" "" "TajikLang.Program"
  WriteRegStr HKCU "Software\Classes\TajikLang.Program" "" "Барномаи TajikLang"
  WriteRegStr HKCU "Software\Classes\TajikLang.Program\DefaultIcon" "" "$INSTDIR\TajikLang Studio.exe,0"
  WriteRegStr HKCU "Software\Classes\TajikLang.Program\shell\open\command" "" '"$INSTDIR\TajikLang Studio.exe" "%1"'

  ReadRegStr $0 HKCU "Environment" "Path"
  StrCpy $1 "$INSTDIR\resources\runtime"
  ${IfThen} $0 == "" ${|} StrCpy $0 $1 ${|}
  ${IfThen} $0 != "" ${|} StrCpy $0 "$1;$0" ${|}
  WriteRegExpandStr HKCU "Environment" "Path" "$0"
  SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=5000
!macroend

!macro customUnInstall
  DeleteRegKey HKCU "Software\Classes\TajikLang.Program"
  DeleteRegValue HKCU "Software\Classes\.tj" ""
  ; The PATH entry is deliberately retained on uninstall only when other
  ; TajikLang runtimes may still be installed; repair/upgrades remain safe.
!macroend
