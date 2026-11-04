; Inno Setup: instalador de Windows para Anonimizador IA
; Se compila con construir_windows.bat (o abriendo este archivo en Inno Setup)

#define AppName "Anonimizador IA"
#define AppVersion "1.0.0"

[Setup]
AppId={{6F1E2B6C-3C7A-4F55-9C2E-AB12CD34EF56}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Anonimizador IA
DefaultDirName={autopf}\AnonimizadorIA
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\AnonimizadorIA.exe
OutputDir=salida
OutputBaseFilename=AnonimizadorIA-Instalador
SetupIconFile=recursos\icono.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "dist\AnonimizadorIA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\AnonimizadorIA.exe"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\AnonimizadorIA.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\AnonimizadorIA.exe"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent
