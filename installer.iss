[Setup]
AppId={{94A06624-C386-4A36-8B77-DAFA7BD306B2}
AppName=FalloutMC Launcher
AppVersion=0.1.0
DefaultDirName={localappdata}\Programs\FalloutMC
DefaultGroupName=FalloutMC
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=dist
OutputBaseFilename=FalloutMC-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\FalloutMC-Launcher.exe
[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
[Files]
Source: "dist\FalloutMC-Launcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "third-party-licenses\*"; DestDir: "{app}\third-party-licenses"; Flags: ignoreversion
[Icons]
Name: "{group}\FalloutMC"; Filename: "{app}\FalloutMC-Launcher.exe"
Name: "{autodesktop}\FalloutMC"; Filename: "{app}\FalloutMC-Launcher.exe"
[Run]
Filename: "{app}\FalloutMC-Launcher.exe"; Description: "Ouvrir FalloutMC"; Flags: nowait postinstall skipifsilent
