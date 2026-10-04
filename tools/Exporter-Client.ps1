$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$Picker = New-Object System.Windows.Forms.FolderBrowserDialog
$Picker.Description = 'Choisis ton dossier CLIENT FalloutMC qui contient mods et kubejs'
if ($Picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit }
$ClientPath = $Picker.SelectedPath
if (-not (Test-Path -LiteralPath (Join-Path $ClientPath 'mods'))) { throw 'Le dossier choisi ne contient pas mods.' }
$ZipPath = Join-Path $PSScriptRoot 'FalloutMC_fichiers_client.zip'
if (Test-Path -LiteralPath $ZipPath) { throw 'FalloutMC_fichiers_client.zip existe déjà : déplace-le avant de refaire un export.' }
$ClientRoot = $ClientPath.TrimEnd('\') + '\'
$SelectedFiles = @()
foreach ($RelativeDirectory in @('mods','kubejs\assets','kubejs\startup_scripts','kubejs\client_scripts')) {
    $Directory = Join-Path $ClientPath $RelativeDirectory
    if (-not (Test-Path -LiteralPath $Directory)) { continue }
    if ((Get-Item -LiteralPath $Directory).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Lien de dossier interdit.' }
    $Directories = New-Object 'System.Collections.Generic.Queue[string]'
    $Directories.Enqueue($Directory)
    while ($Directories.Count -gt 0) {
        $CurrentDirectory = $Directories.Dequeue()
        foreach ($Entry in Get-ChildItem -LiteralPath $CurrentDirectory -Force) {
            if ($Entry.Attributes -band [IO.FileAttributes]::ReparsePoint) { continue }
            if ($Entry.PSIsContainer) { $Directories.Enqueue($Entry.FullName); continue }
            if ($RelativeDirectory -eq 'mods' -and $Entry.Extension -ne '.jar') { continue }
            $SelectedFiles += $Entry
        }
    }
}
$Zip = [IO.Compression.ZipFile]::Open($ZipPath,[IO.Compression.ZipArchiveMode]::Create)
try {
    foreach ($Entry in $SelectedFiles) {
        $RelativeName = $Entry.FullName.Substring($ClientRoot.Length).Replace('\','/')
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($Zip,$Entry.FullName,$RelativeName,[IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
} finally { $Zip.Dispose() }
Write-Host "Export termine : $ZipPath"
Write-Host "Fichiers inclus : $($SelectedFiles.Count). Aucun fichier envoye, aucune installation modifiee."
Write-Host 'Exclus : comptes, mots de passe, monde, config serveur, options personnelles et journaux.'
