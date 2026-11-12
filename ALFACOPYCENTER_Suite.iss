; ALFACOPYCENTER Suite v2.0.13
; Unified installer for ERP Staff, ERP Owner, Banner Studio, Print Surveillance.
; No cloud database deletion, no spooler driver/service modification.
#define CompanyName "ALFACOPYCENTER"
#define SuiteVersion "2.0.13"

[Setup]
AppId=ALFACOPYCENTER.Suite
AppName={#CompanyName} Uygulama Paketi
AppVerName={#CompanyName} Suite {#SuiteVersion}
AppVersion={#SuiteVersion}
VersionInfoVersion=2.0.13.0
DefaultDirName={localappdata}\Programs\ALFACOPYCENTER
DefaultGroupName={#CompanyName}
OutputDir=output
OutputBaseFilename=ALFACOPYCENTER_Suite_Setup_V2_0_13
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
SetupIconFile=assets\icons\alfa_company.ico
AppPublisher={#CompanyName}
AppPublisherURL=https://github.com/alarslan12/alfa-erp
UninstallDisplayIcon={app}\Brand\alfa_company.ico
DisableDirPage=no
DisableProgramGroupPage=yes
UsePreviousTasks=yes
UsePreviousSetupType=yes
UsePreviousLanguage=no
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
ArchitecturesAllowed=x64compatible

[Types]
Name: "full"; Description: "Personel + Afiş Stüdyosu + Yazdırma"
Name: "custom"; Description: "Uygulamaları kendim seçeceğim"; Flags: iscustom

[Components]
Name: "staff"; Description: "ALFA ERP Personel"; Types: full custom
Name: "owner"; Description: "ALFA ERP Yönetici (Firebase owner yetkisi gerekir)"; Types: custom
Name: "banner"; Description: "ALFA Banner Studio Pro v3.13"; Types: full custom
Name: "print"; Description: "ALFA Print Surveillance v2.0"; Types: full custom
Name: "print\agent"; Description: "Windows oturumu arka plan izleyicisi"; Types: full custom

[Tasks]
Name: "printautostart"; Description: "Windows oturumu açılınca yazdırma izleyicisini başlat (önerilir)"; GroupDescription: "Yazdırma izleme:"; Flags: checkedonce; Components: print\agent

[Files]
Source: "dist\AlfaERP\*"; DestDir: "{app}\Staff"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: staff
Source: "dist\AlfaBildirim\*"; DestDir: "{app}\Notifications"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: staff
Source: "dist\AlfaERPYonetici\*"; DestDir: "{app}\Owner"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: owner
Source: "dist\AlfaBannerStudio\*"; DestDir: "{app}\BannerStudio"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: banner
Source: "dist\AlfaPrintSurveillance\*"; DestDir: "{app}\PrintSurveillance"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: print
Source: "dist\AlfaPrintAgent\*"; DestDir: "{app}\PrintAgent"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: print\agent
Source: "dist\AlfaPrintSupervisor\*"; DestDir: "{app}\PrintSupervisor"; Flags: recursesubdirs createallsubdirs ignoreversion; Components: print\agent
Source: "assets\icons\alfa_company.ico"; DestDir: "{app}\Brand"; Flags: ignoreversion
Source: "assets\branding\company.png"; DestDir: "{app}\Brand"; DestName: "ALFACOPYCENTER.png"; Flags: ignoreversion

[Icons]
Name: "{userdesktop}\ALFA ERP Personel"; Filename: "{app}\Staff\AlfaERP.exe"; WorkingDir: "{app}\Staff"; IconFilename: "{app}\Staff\AlfaERP.exe"; Components: staff
Name: "{userprograms}\ALFACOPYCENTER\ERP Personel"; Filename: "{app}\Staff\AlfaERP.exe"; Components: staff
Name: "{userdesktop}\ALFA ERP Yönetici"; Filename: "{app}\Owner\AlfaERPYonetici.exe"; WorkingDir: "{app}\Owner"; Components: owner
Name: "{userprograms}\ALFACOPYCENTER\ERP Yönetici"; Filename: "{app}\Owner\AlfaERPYonetici.exe"; Components: owner
Name: "{userdesktop}\ALFA Banner Studio Pro"; Filename: "{app}\BannerStudio\AlfaBannerStudio.exe"; WorkingDir: "{app}\BannerStudio"; Components: banner
Name: "{userprograms}\ALFACOPYCENTER\Banner Studio"; Filename: "{app}\BannerStudio\AlfaBannerStudio.exe"; Components: banner
Name: "{userdesktop}\ALFA Yazdırma Kontrol"; Filename: "{app}\PrintSurveillance\AlfaPrintSurveillance.exe"; WorkingDir: "{app}\PrintSurveillance"; Components: print
Name: "{userprograms}\ALFACOPYCENTER\Yazdırma Kontrol"; Filename: "{app}\PrintSurveillance\AlfaPrintSurveillance.exe"; Components: print
Name: "{userprograms}\ALFACOPYCENTER\Yazdırma Arka Plan İzleyicisi"; Filename: "{app}\PrintAgent\AlfaPrintAgent.exe"; Components: print\agent
Name: "{userstartup}\ALFA ERP Sipariş Bildirimi"; Filename: "{app}\Notifications\AlfaBildirim.exe"; Components: staff

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ALFA_ERP_Print_Monitor"; ValueData: """{app}\PrintSupervisor\AlfaPrintSupervisor.exe"" --data-dir ""{localappdata}\AlfaERP"""; Flags: uninsdeletevalue; Components: print\agent; Tasks: printautostart

[Run]
Filename: "{app}\Staff\AlfaERP.exe"; Description: "Personel ERP'yi aç"; Flags: nowait postinstall skipifsilent; Components: staff; Check: NotUpdate
Filename: "{app}\Owner\AlfaERPYonetici.exe"; Description: "Yönetici ERP'yi aç"; Flags: nowait postinstall skipifsilent; Components: owner; Check: NotUpdate
Filename: "{app}\BannerStudio\AlfaBannerStudio.exe"; Description: "Banner Studio'yu aç"; Flags: nowait postinstall skipifsilent unchecked; Components: banner; Check: NotUpdate
Filename: "{app}\PrintSurveillance\AlfaPrintSurveillance.exe"; Description: "Yazdırma Kontrol Merkezi'ni aç"; Flags: nowait postinstall skipifsilent unchecked; Components: print; Check: NotUpdate
Filename: "{app}\PrintSupervisor\AlfaPrintSupervisor.exe"; Parameters: "--data-dir ""{localappdata}\AlfaERP"""; Flags: nowait postinstall skipifsilent; Components: print\agent; Tasks: printautostart; Check: NotUpdate
Filename: "{app}\Notifications\AlfaBildirim.exe"; Flags: nowait postinstall skipifsilent; Components: staff; Check: NotUpdate

[Code]
// Edition selection is installation preference, NOT cloud authorization.
// Firebase Auth and RTDB rules verify every owner operation.
function HasCommand(Flag: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount() do
    if CompareText(ParamStr(I),Flag) = 0 then
    begin
      Result := True;
      Exit;
    end;
end;

function NotUpdate(): Boolean;
begin
  Result := not HasCommand('/ALFAUPDATE');
end;

function ExistingSuite(): Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Programs\ALFACOPYCENTER\Brand\ALFACOPYCENTER.png'));
end;

procedure InitializeWizard();
begin
  // Existing suite keeps its previous selected components across upgrades.
  // Only first-time migration from pre-Suite ERP uses the requested edition.
  if ExistingSuite() then Exit;
  if HasCommand('/ALFAOWNER') then
    WizardSelectComponents('owner')
  else if HasCommand('/ALFASTAFF') then
    WizardSelectComponents('staff')
  else if HasCommand('/ALFABANNER') then
    WizardSelectComponents('banner')
  else if HasCommand('/ALFAPRINT') then
    WizardSelectComponents('print,print\agent');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  // Never overwrite any locally cached order, cover, design or print history.
  // Such data lives outside the installer directory.
end;
