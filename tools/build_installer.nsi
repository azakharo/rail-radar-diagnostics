﻿; Script generated by the HM NIS Edit Script Wizard.

; HM NIS Edit Wizard helper defines
Unicode true
!define PRODUCT_NAME "СРППС тест"
!define PRODUCT_VERSION "2.3"
!define PRODUCT_PUBLISHER "ITC Sistema-Sarov"
!define PRODUCT_WEB_SITE "http://sarov-itc.ru/"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\srpps_test.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

; MUI 1.67 compatible ------
!include "MUI.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "..\src\favicon.ico"
!define MUI_UNICON "..\src\favicon.ico"

; Welcome page
!insertmacro MUI_PAGE_WELCOME
; License page
!insertmacro MUI_PAGE_LICENSE "license.txt"
; Directory page
!insertmacro MUI_PAGE_DIRECTORY
; Instfiles page
!insertmacro MUI_PAGE_INSTFILES
; Finish page
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_INSTFILES

; Language files
!insertmacro MUI_LANGUAGE "Russian"

; MUI end ------

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "..\.build\dist\srpps_test_setup.exe"
InstallDir "$PROGRAMFILES\СРППС тест"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
ShowInstDetails show
ShowUnInstDetails show

Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  File "..\.build\dist\srpps_test.exe"
  CreateDirectory "$SMPROGRAMS\СРППС тест"
  CreateShortCut "$SMPROGRAMS\СРППС тест\СРППС тест.lnk" "$INSTDIR\srpps_test.exe"
  ShellLink::SetRunAsAdministrator "$SMPROGRAMS\СРППС тест\СРППС тест.lnk"
  CreateShortCut "$DESKTOP\СРППС тест.lnk" "$INSTDIR\srpps_test.exe"
  ShellLink::SetRunAsAdministrator "$DESKTOP\СРППС тест.lnk"
  File "..\.build\dist\favicon.ico"
  File "..\.build\dist\diagnost.cfg"
SectionEnd

Section -AdditionalIcons
  WriteIniStr "$INSTDIR\${PRODUCT_NAME}.url" "InternetShortcut" "URL" "${PRODUCT_WEB_SITE}"
  CreateShortCut "$SMPROGRAMS\СРППС тест\Website.lnk" "$INSTDIR\${PRODUCT_NAME}.url"
  CreateShortCut "$SMPROGRAMS\СРППС тест\Uninstall.lnk" "$INSTDIR\uninst.exe"
SectionEnd

Section -Post
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\srpps_test.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\srpps_test.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
SectionEnd


Function un.onUninstSuccess
  HideWindow
  MessageBox MB_ICONINFORMATION|MB_OK "$(^Name) was successfully removed from your computer."
FunctionEnd

Function un.onInit
  MessageBox MB_ICONQUESTION|MB_YESNO|MB_DEFBUTTON2 "Are you sure you want to completely remove $(^Name) and all of its components?" IDYES +2
  Abort
FunctionEnd

Section Uninstall
  Delete "$INSTDIR\${PRODUCT_NAME}.url"
  Delete "$INSTDIR\uninst.exe"
  Delete "$INSTDIR\diagnost.cfg"
  Delete "$INSTDIR\favicon.ico"
  Delete "$INSTDIR\srpps_test.exe"

  Delete "$SMPROGRAMS\СРППС тест\Uninstall.lnk"
  Delete "$SMPROGRAMS\СРППС тест\Website.lnk"
  Delete "$DESKTOP\СРППС тест.lnk"
  Delete "$SMPROGRAMS\СРППС тест\СРППС тест.lnk"

  RMDir "$SMPROGRAMS\СРППС тест"
  RMDir "$INSTDIR"

  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
  SetAutoClose true
SectionEnd