<#
.SYNOPSIS
  Exclut de l'analyse en temps reel de Windows Defender les dossiers ecrits en masse par les builds (plan
  temps-compilation, A4) : .pio et .cache du depot, et ~/.platformio (toolchains, ~246 000 fichiers).

.DESCRIPTION
  Chaque compilation lit et ecrit des milliers de fichiers ; l'analyse de chacun ralentit le build sur une machine a
  4 coeurs. Ces dossiers ne contiennent que des fichiers produits par le build ou telecharges par PlatformIO (verifies
  par empreinte). Idempotent : une exclusion deja presente n'est pas rajoutee. A lancer en ADMINISTRATEUR
  (PowerShell « Executer en tant qu'administrateur »), Defender refusant sinon de lire ou d'ecrire ses exclusions.

  Retour arriere : Remove-MpPreference -ExclusionPath <dossier>

.PARAMETER Verifier
  Lecture seule : affiche, pour chaque dossier, s'il est deja exclu. Ne modifie rien.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File outils_docs\scripts_python\maintenance\exclusions_defender.ps1 -Verifier
#>
param([switch]$Verifier)

$depot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$dossiers = @((Join-Path $depot ".pio"), (Join-Path $depot ".cache"), (Join-Path $env:USERPROFILE ".platformio"))

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "REFUS : lancer ce script en administrateur (Defender ne montre ni n'accepte ses exclusions sinon)."
    exit 1
}

$exclus = @((Get-MpPreference).ExclusionPath) | Where-Object { $_ }
$manquants = @()
foreach ($d in $dossiers) {
    $deja = $exclus | Where-Object { $_.TrimEnd('\') -ieq $d.TrimEnd('\') }
    if ($deja) { Write-Host "deja exclu : $d" } else { Write-Host "NON exclu  : $d"; $manquants += $d }
}
if ($Verifier) {
    if ($manquants.Count -eq 0) { Write-Host "Les $($dossiers.Count) dossiers sont exclus." } else { Write-Host "$($manquants.Count) dossier(s) a exclure : relancer sans -Verifier." }
    exit 0
}
foreach ($d in $manquants) {
    Add-MpPreference -ExclusionPath $d
    Write-Host "exclusion ajoutee : $d"
}
Write-Host "Termine. Controle : relancer avec -Verifier."
