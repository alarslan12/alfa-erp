#define MyAppName "ALFA ERP Personel"
#define MyAppVersion "1.1.2"
[Setup]
AppId={{19DBD961-38BC-4D5A-A2FE-7E87D50986E0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\ALFA ERP Personel
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=ALFA_ERP_Personel_Setup_V1_1_2
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
SetupIconFile=assets\icons\alfa_personel.ico
AppPublisher=ALFA ERP
UninstallDisplayIcon={app}\AlfaERP.exe
SetupLogging=yes
DisableWelcomePage=no
DisableReadyPage=no
DisableProgramGroupPage=yes
[Files]
Source: "dist\AlfaERP\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "dist\AlfaBildirim\*"; DestDir: "{app}\Bildirim"; Flags: recursesubdirs createallsubdirs ignoreversion
[Icons]
Name: "{userdesktop}\ALFA ERP Personel"; Filename: "{app}\AlfaERP.exe"; WorkingDir: "{app}"; Comment: "ALFA ERP Personel uygulamasını aç"
Name: "{userprograms}\ALFA ERP Personel"; Filename: "{app}\AlfaERP.exe"; WorkingDir: "{app}"; Comment: "ALFA ERP Personel uygulamasını aç"
Name: "{userstartup}\ALFA ERP Bildirim"; Filename: "{app}\Bildirim\AlfaBildirim.exe"; WorkingDir: "{app}\Bildirim"
[Run]
Filename: "{app}\AlfaERP.exe"; Description: "ALFA ERP Personel uygulamasını başlat"; Flags: nowait postinstall skipifsilent
Filename: "{app}\Bildirim\AlfaBildirim.exe"; Description: "Sipariş bildirim sistemini başlat"; Flags: nowait postinstall skipifsilent
