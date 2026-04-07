[Setup]
AppName=Bistek Printer System
AppVersion=2.0
DefaultDirName=C:\BistekPrinter
DefaultGroupName=BistekPrinter
DisableProgramGroupPage=yes
; O instalador vai rodar como administrador para poder mexer no C: e Nginx
PrivilegesRequired=admin
OutputBaseFilename=Instalador_Bistek_PDV
OutputDir=..\

[Files]
; Captura o Nginx base de produção (que fará o SSL Pass para o Python)
Source: "..\nginx\*"; DestDir: "{app}\nginx"; Flags: ignoreversion recursesubdirs createallsubdirs
; Captura as Ferramentas Extras
Source: "..\ferramentas\*"; DestDir: "{app}\certs"; Flags: ignoreversion recursesubdirs createallsubdirs
; Captura toda a compilação do Backend Python (Junto ao Front Clássico, ofuscado pelo cx_Freeze)
Source: "..\build\*"; DestDir: "{app}\api"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Bistek Printer (Parar-Iniciar)"; Filename: "{app}\nginx\Restart_Bistek.bat"
Name: "{commondesktop}\Bistek Printer (Operação)"; Filename: "https://localhost"; IconFilename: "{app}\api\logo.ico"
; Injeção Sólida no Auto-Run do Windows (Inicializar com o Sistema) com os Diretórios de Trabalho perfeitos!
Name: "{autostartup}\Bistek_Nginx_Engine"; Filename: "{app}\nginx\nginx.exe"; WorkingDir: "{app}\nginx";
Name: "{autostartup}\Bistek_Python_API"; Filename: "{app}\api\BistekPrinter.exe"; WorkingDir: "{app}\api";

[Code]
var
  ConfigPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  // Cria a página de configuração dinâmica
  ConfigPage := CreateInputQueryPage(wpSelectDir,
    'Configuração Segura de PDV', 'Autenticação e Rede (Loja)',
    'Por favor, insira o IP que a balança e os celulares usarão para acessar a API, e o Token Master da BAPI:');
  
  ConfigPage.Add('IP Local desta Máquina (Ex: 192.168.0.188):', False);
  ConfigPage.Add('Token da BAPI (Secret):', False);
  ConfigPage.Add('URL base da BAPI:', False);
  
  ConfigPage.Values[0] := '127.0.0.1'; 
  ConfigPage.Values[1] := ''; 
  ConfigPage.Values[2] := 'https://api.bistek.com.br';
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  NginxRawData: AnsiString;
  NginxConfigString: String;
  AppIP, AppToken, AppURL: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    AppIP := ConfigPage.Values[0];
    AppToken := ConfigPage.Values[1];
    AppURL := ConfigPage.Values[2];

    // 1. GERAR CERTIFICADOS TLS OBRIGATÓRIOS PARA ZEBRA NA HORA
    // Executa e aguarda o mkcert instalar a Raiz de Confiança Local
    Exec(ExpandConstant('{app}\certs\mkcert.exe'), '-install', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    // Emite o certificado assinado atrelado ao IP Local digitado!
    Exec(ExpandConstant('{app}\certs\mkcert.exe'), '-cert-file certificate.crt -key-file private.key ' + AppIP + ' localhost 127.0.0.1', ExpandConstant('{app}\nginx\conf'), SW_HIDE, ewWaitUntilTerminated, ResultCode);

    // 2. MODIFICAR NGINX ON THE FLY (Substituição de String Inteligente no conf)
    if LoadStringFromFile(ExpandConstant('{app}\nginx\conf\nginx.conf'), NginxRawData) then
    begin
      NginxConfigString := String(NginxRawData);
      StringChangeEx(NginxConfigString, 'REPLACE_ME_IP', AppIP, True);
      NginxRawData := AnsiString(NginxConfigString);
      SaveStringToFile(ExpandConstant('{app}\nginx\conf\nginx.conf'), NginxRawData, False);
    end;

    // 3. ABASTECER O COFRE PYTHON (Chamada de Linha de Comando Oculta!)
    // Invoca o cx_freeze exe rodando o parser argparse via --setup invés de pedir input iterativo!
    Exec(ExpandConstant('{app}\api\BistekPrinter.exe'), '--setup --url "' + AppURL + '" --token "' + AppToken + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    // 4. INSTALANDO SERVIÇO EM SEGUNDO PLANO
    // Neste estágio você pode opcionalmente ativar o NSSM ou AutoRun do Windows Registry.
  end;
end;
