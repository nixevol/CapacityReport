!macro NSIS_HOOK_PREUNINSTALL
  nsExec::ExecToLog 'taskkill /F /T /IM capacity-report-desktop.exe'
  nsExec::ExecToLog 'taskkill /F /T /IM capareport-server.exe'
!macroend

!macro NSIS_HOOK_POSTUNINSTALL
  MessageBox MB_YESNO|MB_ICONQUESTION "是否同时删除本机用户数据？$\r$\n$\r$\n这将删除配置、脚本、授权、缓存和日志：$\r$\n$APPDATA\com.nixevol.capacityreport" IDYES DeleteUserData IDNO Done
  DeleteUserData:
    RMDir /r "$APPDATA\com.nixevol.capacityreport"
  Done:
!macroend
