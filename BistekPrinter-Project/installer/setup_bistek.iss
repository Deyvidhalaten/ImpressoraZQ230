; ---------------------------------------------------------
; SCRIPT DE INSTALAÇÃO - BISTEK PRINTER SYSTEM v3.3.1
; Desenvolvido por: Deyvid Silva (TI Bistek)
; ---------------------------------------------------------

[Setup]
AppName=Bistek Printer System
AppVersion=3.3.3
DefaultDirName=C:\BistekPrinter
DefaultGroupName=BistekPrinter
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputBaseFilename=Instalador_BistekPrinter
OutputDir=..\
Compression=lzma
SolidCompression=yes

[Files]
; 1. Nginx
Source: "..\nginx\*"; DestDir: "{app}\nginx"; Flags: ignoreversion recursesubdirs createallsubdirs
; 2. Ferramentas (mkcert)
Source: "..\ferramentas\mkcert.exe"; DestDir: "{app}\tools"; Flags: ignoreversion
; 3. Backend Python (O executável principal)
Source: "..\build\*"; DestDir: "{app}\api"; Flags: ignoreversion recursesubdirs createallsubdirs
; 4. FRONTEND (Ajuste: Adicionando a pasta que estava faltando no instalador)
Source: "..\frontend\*"; DestDir: "{app}\api\frontend"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "{app}"; Permissions: users-full
Name: "{app}\appdata"; Permissions: users-full
Name: "{app}\nginx\temp"; Permissions: users-full
Name: "{app}\nginx\temp\client_body_temp"; Permissions: users-full
Name: "{app}\nginx\temp\proxy_temp"; Permissions: users-full
Name: "{app}\nginx\temp\fastcgi_temp"; Permissions: users-full
Name: "{app}\nginx\logs"; Permissions: users-full

[Icons]
Name: "{group}\Reiniciar Servidor Bistek"; Filename: "{app}\nginx\Restart_Bistek.bat"
Name: "{commondesktop}\Bistek Printer (Operação)"; Filename: "https://{code:GetAppIP}/frontend/"; IconFilename: "{app}\api\logo.ico"

Name: "{autostartup}\Bistek_Nginx"; Filename: "{app}\nginx\nginx.exe"; Parameters: "-p ""{app}\nginx"""; WorkingDir: "{app}\nginx"; Flags: runminimized
Name: "{autostartup}\Bistek_API"; Filename: "{app}\api\BistekPrinter.exe"; WorkingDir: "{app}\api"; Flags: runminimized

[Registry]
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "BistekNginx"; ValueData: """{app}\nginx\nginx.exe"" -p ""{app}\nginx"""; Flags: uninsdeletevalue
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "BistekAPI"; ValueData: """{app}\api\BistekPrinter.exe"""; Flags: uninsdeletevalue

[Run]
Filename: "{app}\nginx\nginx.exe"; Parameters: "-p ""{app}\nginx"""; WorkingDir: "{app}\nginx"; Flags: nowait runhidden
Filename: "{app}\api\BistekPrinter.exe"; WorkingDir: "{app}\api"; Flags: nowait

[Code]
var
  ConfigPage: TInputQueryWizardPage;

function GetAppIP(Param: String): String;
begin
  Result := Trim(ConfigPage.Values[0]);
  if Result = '' then Result := '127.0.0.1';
end;

procedure InitializeWizard;
begin
  ConfigPage := CreateInputQueryPage(wpSelectDir,
    'Configuração Segura do Sistema', 'Rede e Autenticação',
    'Informe o IP desta máquina para o certificado SSL e os dados da BAPI (Se vazio, usará 127.0.0.1):');
  
  ConfigPage.Add('IP Local desta Máquina (Ex: 10.17.30.2):', False);
  ConfigPage.Add('Token Master da BAPI:', False);
  ConfigPage.Add('URL Base da BAPI:', False);
  
  ConfigPage.Values[0] := '10.17.30.2'; 
  ConfigPage.Values[2] := 'https://api.bistek.com.br';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  NginxConfigAnsi: AnsiString;
  NginxConfigUnicode: String;
  AppIP, AppToken, AppURL: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    AppIP := Trim(ConfigPage.Values[0]);
    AppToken := ConfigPage.Values[1];
    AppURL := ConfigPage.Values[2];

    if AppIP = '' then AppIP := '127.0.0.1';

    // --- PASSO 1: GERAR CERTIFICADO ---
    Exec(ExpandConstant('{app}\tools\mkcert.exe'), '-install', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    
    // Caminho direto na CONF para não precisar de prefixo /certs
    Exec(ExpandConstant('{app}\tools\mkcert.exe'), 
         '-cert-file certificate.crt -key-file private.key ' + AppIP + ' localhost 127.0.0.1', 
         ExpandConstant('{app}\nginx\conf'), 
         SW_HIDE, ewWaitUntilTerminated, ResultCode);

    // --- PASSO 2: PATCH NO NGINX.CONF ---
    if LoadStringFromFile(ExpandConstant('{app}\nginx\conf\nginx.conf'), NginxConfigAnsi) then
    begin
      NginxConfigUnicode := String(NginxConfigAnsi);
      // O StringChangeEx com o último parâmetro True substitui TODAS as ocorrências do IP
      StringChangeEx(NginxConfigUnicode, 'REPLACE_ME_IP', AppIP, True);
      SaveStringToFile(ExpandConstant('{app}\nginx\conf\nginx.conf'), AnsiString(NginxConfigUnicode), False);
    end;

    // --- PASSO 3: CONFIGURAR BACKEND ---
    Exec(ExpandConstant('{app}\api\BistekPrinter.exe'), 
         '--setup --url "' + AppURL + '" --token "' + AppToken + '"', 
         ExpandConstant('{app}\api'), 
         SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;