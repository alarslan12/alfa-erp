#define MyAppName "ALFA ERP Yönetici"
#define MyAppVersion "6.1.6"
[Setup]
AppId={{E151CC0D-9154-42D0-BF2F-E01CE71C5C36}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\ALFA ERP Yönetici
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=ALFA_ERP_Yonetici_Setup_V6_1_6
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
UninstallDisplayIcon={app}\AlfaERPYonetici.exe
[Files]
Source: "dist\AlfaERPYonetici\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "YONETICI_SURUMU.flag"; DestDir: "{app}"; Flags: ignoreversion
[Icons]
Name: "{autodesktop}\ALFA ERP Yönetici"; Filename: "{app}\AlfaERPYonetici.exe"; WorkingDir: "{app}"
[Run]
Filename: "{app}\AlfaERPYonetici.exe"; Description: "ALFA ERP Yönetici aç"; Flags: postinstall nowait skipifsilent
