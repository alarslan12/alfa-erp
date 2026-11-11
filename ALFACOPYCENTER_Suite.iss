; ALFACOPYCENTER Suite v2.0.2
; Unified installer for ERP Staff, ERP Owner, Banner Studio, Print Surveillance.
; No cloud database deletion, no spooler driver/service modification.
#define CompanyName "ALFACOPYCENTER"
#define SuiteVersion "2.0.8"

[Setup]
AppId=ALFACOPYCENTER.Suite
AppName={#CompanyName} Uygulama Paketi
AppVerName={#CompanyName} Suite {#SuiteVersion}
AppVersion={#SuiteVersion}
VersionInfoVersion=2.0.8.0
DefaultDirName={localappdata}\Programs\ALFACOPYCENTER
DefaultGroupName={#CompanyName}
OutputDir=output
OutputBaseFilename=ALFACOPYCENTER_Suite_Setup_V2_0_8
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
Name: "owner"; Description: "ALFA ERP Yönetici (kurulum parolası gerekir)"; Types: custom
Name: "banner"; Description: "ALFA Banner Studio Pro v3.9"; Types: full custom
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
var
  OwnerPasswordPage: TInputQueryWizardPage;

function HasCommand(Flag: String): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount() do
    if CompareText(ParamStr(I), Flag) = 0 then
    begin
      Result := True;
      Exit;
    end;
end;

function NotUpdate(): Boolean;
begin
  Result := not HasCommand('/ALFAUPDATE');
end;

function OwnerPasswordValid(): Boolean;
begin
  Result := CompareText(
    GetSHA256OfString(
      'ALFA-ERP-OWNER-SETUP-v1-4a81f7|' + OwnerPasswordPage.Values[0]),
    '60d251ed1c49cd140d00d6caae45f13bbab68322b0735f03b4142e2fe36210a7'
  ) = 0;
end;

procedure InitializeWizard();
begin
  OwnerPasswordPage := CreateInputQueryPage(wpSelectComponents,
    'Yönetici kurulumu', 'Yönetici ERP için ek kurulum doğrulaması',
    'Yalnız seçili Yönetici bileşeni için parola sorulur. Bulut yönetici '
    + 'yetkisi Firebase rolüyle ayrıca denetlenir.');
  OwnerPasswordPage.Add('Yönetici kurulum parolası:', True);

  // Legacy ALFA ERP update helper requests its existing edition.
  // Unlike a silent shortcut it never bypasses owner verification.
  if HasCommand('/ALFAOWNER') then
    WizardSelectComponents('owner,banner,print,print\agent')
  else if HasCommand('/ALFASTAFF') then
    WizardSelectComponents('staff,banner,print,print\agent')
  else if HasCommand('/ALFABANNER') then
    WizardSelectComponents('banner');
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = OwnerPasswordPage.ID) and
            (not WizardIsComponentSelected('owner'));
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if (CurPageID = OwnerPasswordPage.ID) and
      WizardIsComponentSelected('owner') then
  begin
    Result := OwnerPasswordValid();
    if not Result then
      MsgBox('Yönetici kurulum parolası geçersiz.', mbError, MB_OK);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if WizardIsComponentSelected('owner') and not OwnerPasswordValid() then
    Result := 'Yönetici kurulum parolası gerekli.';
end;
