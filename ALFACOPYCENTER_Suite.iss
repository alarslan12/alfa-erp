; ALFACOPYCENTER Suite v2.0.16
; Unified installer for ERP Staff, ERP Owner, Banner Studio, Print Surveillance.
; No cloud database deletion, no spooler driver/service modification.
#define CompanyName "ALFACOPYCENTER"
#define SuiteVersion "2.0.16"

[Setup]
AppId=ALFACOPYCENTER.Suite
AppName={#CompanyName} Uygulama Paketi
AppVerName={#CompanyName} Suite {#SuiteVersion}
AppVersion={#SuiteVersion}
VersionInfoVersion=2.0.16.0
DefaultDirName={localappdata}\Programs\ALFACOPYCENTER
DefaultGroupName={#CompanyName}
OutputDir=output
OutputBaseFilename=ALFACOPYCENTER_Suite_Setup_V2_0_16
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
// This is a LOCAL installation gate, never a Firebase owner credential.
// Only salted SHA-256 is in the public installer. Actual administration
// still requires an approved Firebase owner UID and enforced RTDB Rules.
var
  OwnerPasswordPage: TInputQueryWizardPage;

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

function OwnerPasswordValid(): Boolean;
begin
  Result := False;
  if OwnerPasswordPage = nil then Exit;
  Result := CompareText(
    GetSHA256OfString('a4ecb2ecc3dfffea67714300b885c976|' + OwnerPasswordPage.Values[0]),
    'ab43d44863bf59ba4219ece29961fe8d691fbefd26c0b9d7db1dea3c498ee712') = 0;
end;

procedure InitializeWizard();
begin
  OwnerPasswordPage := CreateInputQueryPage(wpSelectComponents,
    'Yönetici kurulumu',
    'Yönetici bileşenini kurmak için yerel kurulum şifresi gerekli',
    'Bu şifre yalnızca Yönetici bileşeninin kurulumunu korur. ' +
    'Firebase owner yetkisi ayrıca Cloud Shell üzerinden verilmelidir.');
  OwnerPasswordPage.Add('Yönetici kurulum şifresi:', True);

  // Inno remembers selected components from existing Suite installs.
  // Only first-time migration selects the requested edition.
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

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = OwnerPasswordPage.ID) and
            (not WizardIsComponentSelected('owner'));
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = OwnerPasswordPage.ID) and WizardIsComponentSelected('owner') then
  begin
    Result := OwnerPasswordValid();
    if not Result then
      MsgBox('Yönetici kurulum şifresi yanlış. Kuruluma devam edilemez.', mbError, MB_OK);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  // Second gate also runs for /SILENT and /VERYSILENT, so the
  // password page cannot be skipped to install the owner component.
  if WizardIsComponentSelected('owner') and not OwnerPasswordValid() then
    Result := 'Yönetici bileşeni seçildi. Doğru yerel kurulum şifresi gerekli.';
  // Customer data is always stored outside the installation folder.
end;
