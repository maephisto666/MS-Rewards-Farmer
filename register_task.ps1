<#
.SYNOPSIS
    Registers (or updates) a Windows Task Scheduler task that runs MS-Rewards-Farmer
    automatically.

.DESCRIPTION
    Replaces the previous "generate an XML file and import it manually" workflow
    (generate_task_xml.py). This script creates the scheduled task directly via the
    native ScheduledTasks cmdlets in a single step, and is idempotent: re-running it
    updates the existing task in place (-Force).

    The task is configured to run *whether or not the user is logged on*. Windows
    requires the account password to be stored for this, so the script prompts for it
    securely. Because the task then runs in a non-interactive session (no visible
    desktop), MS-Rewards-Farmer must run in headless mode (the default:
    `browser.visible: false`). Visible-mode runs will not work without an
    interactive logon.

.PARAMETER TaskName
    Name of the scheduled task. Default: "MS-Rewards-Farmer".

.PARAMETER Schedule
    When the task fires:
      Daily   - once a day at -RunAt (default)
      Startup - shortly after the computer boots (see -StartupDelay)

    Note: only one trigger is used on purpose. Running the bot twice in close succession
    (e.g. daily + startup) would overlap with no mutual exclusion and hammer the Microsoft
    endpoints, which can get the activity flagged as suspicious.

.PARAMETER RunAt
    Daily start time (24h "HH:mm"), used when -Schedule is Daily. Default: "03:00".

.PARAMETER StartupDelay
    ISO-8601 delay applied to the startup trigger so networking is up before the run
    (e.g. "PT5M" = 5 minutes). Used when -Schedule is Startup. Default: "PT5M".

.PARAMETER UserId
    Account to run the task as. Accepts "user", "COMPUTER\user" or "DOMAIN\user".
    Default: the current user on the local machine.

.PARAMETER TargetScript
    The PowerShell script the task launches, relative to this script's folder or an
    absolute path. Default: "run.ps1".

.PARAMETER ScriptArgs
    Arguments passed to the target script. Default: "-r <Retries>". Pass a single space
    (" ") to launch the target with no arguments.

.PARAMETER Retries
    Convenience value used to build the default -ScriptArgs ("-r <Retries>"). Default: 3.

.PARAMETER RunLevel
    Privilege level: "Limited" (default) or "Highest" (elevated). run.ps1 does not need
    elevation; use "Highest" only if your target script does.

.EXAMPLE
    # Public default: daily at 06:00, run.ps1, non-elevated. From an elevated PowerShell:
    .\register_task.ps1

.EXAMPLE
    # Fire shortly after boot instead of at a fixed time:
    .\register_task.ps1 -Schedule Startup

.EXAMPLE
    # Point at a different launcher that needs elevation, no script args:
    .\register_task.ps1 -TargetScript my-launcher.ps1 -RunLevel Highest -ScriptArgs " "

.NOTES
    Run from an elevated (Administrator) PowerShell. Registering a task that runs
    while logged off stores credentials and requires the "Log on as a batch job"
    right, which normally needs elevation.
#>

[CmdletBinding()]
param(
    [string]$TaskName = "MS-Rewards-Farmer",
    [ValidateSet("Daily", "Startup")][string]$Schedule = "Daily",
    [string]$RunAt = "03:00",
    [string]$StartupDelay = "PT5M",
    [string]$UserId = "$env:USERNAME",
    [string]$TargetScript = "run.ps1",
    [string]$ScriptArgs = "",
    [int]$Retries = 3,
    [ValidateSet("Limited", "Highest")][string]$RunLevel = "Limited"
)

$ErrorActionPreference = "Stop"

# --- Resolve paths relative to this script, so CWD does not matter ---------------
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$target = if ([System.IO.Path]::IsPathRooted($TargetScript)) {
    $TargetScript
} else {
    Join-Path $scriptDir $TargetScript
}

if (-not (Test-Path $target)) {
    throw "Could not find target script at '$target'. Run register_task.ps1 from the repository root, or pass -TargetScript."
}

# --- Warn (do not block) if not elevated ----------------------------------------
$isAdmin = ([Security.Principal.WindowsPrincipal] `
        [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Warning "Not running as Administrator. Registering a 'run whether logged on or not' task usually requires elevation; if registration fails, re-run from an elevated PowerShell."
}

# --- Normalise the principal to COMPUTER\user (or keep DOMAIN\user) --------------
$fullUser = if ($UserId -match '\\') { $UserId } else { "$env:COMPUTERNAME\$UserId" }

# --- Prompt for the Windows password securely (needed for logged-off runs) -------
$securePass = Read-Host -AsSecureString "Windows password for $fullUser"
$plainPass = [System.Net.NetworkCredential]::new('', $securePass).Password
if ([string]::IsNullOrEmpty($plainPass)) {
    throw "An empty password was provided. A password is required to run the task while logged off."
}

# --- Build the action ------------------------------------------------------------
$argLine = if ([string]::IsNullOrWhiteSpace($ScriptArgs)) { "-r $Retries" } else { $ScriptArgs.Trim() }
$psArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$target`""
if ($argLine) { $psArgs += " $argLine" }

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument $psArgs `
    -WorkingDirectory $scriptDir

# --- Build the trigger -----------------------------------------------------------
# A single trigger by design: a daily + startup combo would run the bot twice with no
# mutual exclusion and overload the Microsoft endpoints, risking a suspicious-activity flag.
if ($Schedule -eq "Daily") {
    $trigger = New-ScheduledTaskTrigger -Daily -At $RunAt
} else {
    $trigger = New-ScheduledTaskTrigger -AtStartup
    if ($StartupDelay) { $trigger.Delay = $StartupDelay }
}

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit ([TimeSpan]::Zero)   # no time limit

try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -User $fullUser `
        -Password $plainPass `
        -RunLevel $RunLevel `
        -Description "MS-Rewards-Farmer: runs Bing searches and daily activities to farm Microsoft Rewards points." `
        -Force | Out-Null
}
finally {
    # Scrub the plaintext password from memory regardless of success/failure.
    $plainPass = $null
    [System.GC]::Collect()
}

$when = switch ($Schedule) {
    "Daily" { "daily at $RunAt" }
    "Startup" { "at startup (+$StartupDelay)" }
}

Write-Host ""
Write-Host "Scheduled task '$TaskName' registered." -ForegroundColor Green
Write-Host "  Runs    : $when"
Write-Host "  As user : $fullUser (whether or not you are logged on)"
Write-Host "  Level   : $RunLevel"
Write-Host "  Action  : $(Split-Path -Leaf $target) $argLine"
Write-Host ""
Write-Host "Note: because the task runs in a non-interactive session, keep MS-Rewards-Farmer"
Write-Host "in headless mode (browser.visible: false). To remove the task later, run:"
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
