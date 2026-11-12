#define MyAppName "ALFA ERP"
#define MyAppVersion "1.1.2"

[Setup]
; Keep the old edition-specific AppIds and install paths so upgrades preserve
; existing Windows shortcuts/uninstall data and never touch %LOCALAPPDATA%\AlfaERP.
AppId={code:EditionAppId}
UsePreviousLanguage=no
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName=ALFA ERP v1.1.2
DefaultDirName={code:EditionDirectory}
DefaultGroupName=ALFA ERP
OutputDir=output
OutputBaseFilename=ALFA_ERP_Setup_V1_1_2
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
SetupIconFile=assets\icons\alfa_personel.ico
AppPublisher=ALFA ERP
UninstallDisplayIcon={app}\{code:EditionExe}
DisableDirPage=yes
DisableProgramGroupPage=yes
SetupLogging=yes
CloseApplications=yes
RestartApplications=no

[Files]
Source: "dist\AlfaERP\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Check: IsStaff
Source: "dist\AlfaBildirim\*"; DestDir: "{app}\Bildirim"; Flags: recursesubdirs createallsubdirs ignoreversion; Check: IsStaff
Source: "dist\AlfaERPYonetici\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion; Check: IsOwner

[Icons]
Name: "{userdesktop}\ALFA ERP Personel"; Filename: "{app}\AlfaERP.exe"; WorkingDir: "{app}"; Check: IsStaff
Name: "{userprograms}\ALFA ERP Personel"; Filename: "{app}\AlfaERP.exe"; WorkingDir: "{app}"; Check: IsStaff
Name: "{userstartup}\ALFA ERP Bildirim"; Filename: "{app}\Bildirim\AlfaBildirim.exe"; WorkingDir: "{app}\Bildirim"; Check: IsStaff
Name: "{userdesktop}\ALFA ERP Yönetici"; Filename: "{app}\AlfaERPYonetici.exe"; WorkingDir: "{app}"; Check: IsOwner
Name: "{userprograms}\ALFA ERP Yönetici"; Filename: "{app}\AlfaERPYonetici.exe"; WorkingDir: "{app}"; Check: IsOwner

[Run]
Filename: "{app}\AlfaERP.exe"; Description: "ALFA ERP Personel uygulamasını aç"; Flags: nowait postinstall skipifsilent; Check: RunStaff
Filename: "{app}\Bildirim\AlfaBildirim.exe"; Description: "Sipariş bildiricisini başlat"; Flags: nowait postinstall skipifsilent; Check: RunStaff
Filename: "{app}\AlfaERPYonetici.exe"; Description: "ALFA ERP Yönetici uygulamasını aç"; Flags: nowait postinstall skipifsilent; Check: RunOwner

[Code]
var
  EditionPage: TInputOptionWizardPage;

function IsOwner(): Boolean;
begin
  Result := (EditionPage <> nil) and (EditionPage.SelectedValueIndex = 1);
end;

function IsStaff(): Boolean;
begin
  Result := not IsOwner();
end;

function HasUpdateFlag(): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 1 to ParamCount() do
    if CompareText(ParamStr(I), '/ALFAUPDATE') = 0 then
    begin
      Result := True;
      Exit;
    end;
end;

function RunStaff(): Boolean;
begin
  Result := IsStaff() and not HasUpdateFlag();
end;

function RunOwner(): Boolean;
begin
  Result := IsOwner() and not HasUpdateFlag();
end;

function EditionAppId(Param: String): String;
begin
  if IsOwner() then
    Result := '{E151CC0D-9154-42D0-BF2F-E01CE71C5C36}'
  else
    Result := '{19DBD961-38BC-4D5A-A2FE-7E87D50986E0}';
end;

function EditionDirectory(Param: String): String;
begin
  if IsOwner() then
    Result := ExpandConstant('{localappdata}\Programs\ALFA ERP Yönetici')
  else
    Result := ExpandConstant('{localappdata}\Programs\ALFA ERP Personel');
end;

function EditionExe(Param: String): String;
begin
  if IsOwner() then
    Result := 'AlfaERPYonetici.exe'
  else
    Result := 'AlfaERP.exe';
end;

procedure InitializeWizard();
var
  I: Integer;
begin
  EditionPage := CreateInputOptionPage(wpWelcome,
    'Kurulum türü', 'Bu bilgisayara hangi ALFA ERP sürümü kurulacak?',
    'Yönetici erişimi Firebase üzerinde onaylı owner rolüyle korunur.',
    True, False);
  EditionPage.Add('Personel (sipariş, katalog, bildirimler)');
  EditionPage.Add('Yönetici (yönetim, cihazlar, hata merkezi)');
  EditionPage.SelectedValueIndex := 0;
  for I := 1 to ParamCount() do
    if CompareText(ParamStr(I), '/ALFAOWNER') = 0 then
      EditionPage.SelectedValueIndex := 1;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = EditionPage.ID then
    WizardForm.DirEdit.Text := EditionDirectory('');
end;
