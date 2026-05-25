!macro ResolveCapacityReportInstallDir
  ${If} ${FileExists} "D:\*.*"
    StrCpy $R9 "D:\Program Files\${PRODUCTNAME}"
  ${Else}
    ${If} ${RunningX64}
      StrCpy $R9 "$PROGRAMFILES64\${PRODUCTNAME}"
    ${Else}
      StrCpy $R9 "$PROGRAMFILES\${PRODUCTNAME}"
    ${EndIf}
  ${EndIf}
!macroend

!macro NSIS_HOOK_PREINSTALL
  !insertmacro ResolveCapacityReportInstallDir
  StrCpy $INSTDIR "$R9"
  SetOutPath "$INSTDIR"
!macroend

!macro NSIS_HOOK_POSTINSTALL
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCTNAME}"
  DeleteRegKey HKCU "Software\${MANUFACTURER}\${PRODUCTNAME}"
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  nsExec::ExecToLog 'taskkill /F /T /IM capacity-report-desktop.exe'
  nsExec::ExecToLog 'taskkill /F /T /IM capareport-server.exe'
!macroend

!macro NSIS_HOOK_POSTUNINSTALL
  MessageBox MB_YESNO|MB_ICONQUESTION "是否同时删除本机用户数据？" IDYES DeleteUserData IDNO Done
  DeleteUserData:
    RMDir /r "$APPDATA\com.nixevol.capacityreport"
  Done:
!macroend
