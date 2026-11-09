# Enregistre (ou supprime) la tâche planifiée de veille quotidienne.
# Usage :  powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1 [-Time "08:00"] [-Remove]
param(
    [string]$Time = "08:00",
    [switch]$Remove
)

$TaskName = "StageAgent-VeilleQuotidienne"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Tâche '$TaskName' supprimée."
    exit 0
}

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Python du venv introuvable : $Python" }

$Action = New-ScheduledTaskAction -Execute $Python -Argument "run_daily.py" -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
# StartWhenAvailable : si le PC était éteint à l'heure prévue, la veille se lance au prochain démarrage
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "Veille quotidienne des offres de stage (Stage Agent)" -Force | Out-Null

Write-Host "Tâche '$TaskName' enregistrée : tous les jours à $Time."
Write-Host "Test immédiat : Start-ScheduledTask -TaskName $TaskName"
Write-Host "Résultats : logs\derniere_veille.txt et candidatures.md"
