#define MyAppName "Insurance Manager Backend"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Insurance Manager"
#define MyAppExeName "InsuranceBackendService.exe"

[Setup]
AppId={{8D57304A-BA40-4C52-8B40-8D4E9823D91F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\InsuranceManagerBackend
DefaultGroupName=Insurance Manager Backend
DisableProgramGroupPage=yes
OutputDir=..\installer_output
OutputBaseFilename=InsuranceManagerBackendSetup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
SetupIconFile=InsuranceManager.ico
UninstallDisplayIcon={app}\InsuranceManager.ico

[Dirs]
Name: "{app}\logs"; Permissions: users-modify
Name: "{app}\config"
Name: "{app}\frontend_dist"

[Files]
Source: "..\backend\*"; DestDir: "{app}\backend"; Flags: recursesubdirs createallsubdirs ignoreversion; Excludes: "__pycache__\*,*.pyc,tests\*,.pytest_cache\*"
Source: "..\installer_staging\frontend_dist\*"; DestDir: "{app}\frontend_dist"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\config\backend_service_config.json"; DestDir: "{app}\config"; Flags: ignoreversion onlyifdoesntexist
Source: "..\scripts\windows\windows_service.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\scripts\windows\install_service.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\scripts\windows\uninstall_service.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\scripts\windows\start_service.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\scripts\windows\stop_service.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "InsuranceManager.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\InsuranceBackendService\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Open Insurance Manager"; Filename: "{win}\explorer.exe"; Parameters: """http://127.0.0.1:8000/"""; IconFilename: "{app}\InsuranceManager.ico"
Name: "{group}\Start Backend Service"; Filename: "{app}\start_service.bat"; WorkingDir: "{app}"; IconFilename: "{app}\InsuranceManager.ico"
Name: "{group}\Stop Backend Service"; Filename: "{app}\stop_service.bat"; WorkingDir: "{app}"; IconFilename: "{app}\InsuranceManager.ico"
Name: "{group}\Open Logs Folder"; Filename: "{app}\logs"; IconFilename: "{app}\InsuranceManager.ico"
Name: "{group}\Open Config File"; Filename: "notepad.exe"; Parameters: """{app}\config\backend_service_config.json"""; IconFilename: "{app}\InsuranceManager.ico"

[Run]
Filename: "{app}\install_service.bat"; WorkingDir: "{app}"; Flags: runhidden waituntilterminated
Filename: "{app}\start_service.bat"; WorkingDir: "{app}"; Flags: runhidden waituntilterminated

[UninstallRun]
Filename: "{app}\stop_service.bat"; WorkingDir: "{app}"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "StopInsuranceBackendService"
Filename: "{app}\uninstall_service.bat"; WorkingDir: "{app}"; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "RemoveInsuranceBackendService"
