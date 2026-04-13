# career-ops-kr Windows 작업 스케줄러 자동 등록
# 실행: PowerShell을 관리자 권한으로 열고 .\scripts\setup_windows_cron.ps1

# 프로젝트 루트 = 이 스크립트가 있는 scripts/의 상위 디렉토리
$ProjectDir = Split-Path -Parent $PSScriptRoot
$PythonEnv = Join-Path $ProjectDir ".venv\Scripts\python.exe"

# 없으면 uv python fallback
if (-not (Test-Path $PythonEnv)) {
    $PythonEnv = "python"
}

# ── Task 1: 매일 09:00 전체 스캔 + 엑셀 출력 ─────────────────────────────────
$DailyScript = @"
cd '$ProjectDir'
`$env:PYTHONIOENCODING = 'utf-8'
uv run career-ops scan --site linkareer
uv run career-ops scan --site saramin
uv run career-ops scan --site wanted
uv run career-ops export --open-only -o `"`$env:USERPROFILE\Desktop\공고현황_최신.xlsx`"
"@

$DailyScriptPath = "$ProjectDir\scripts\_daily_scan.ps1"
$DailyScript | Out-File -FilePath $DailyScriptPath -Encoding UTF8 -Force

$Action1 = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$DailyScriptPath`""

$Trigger1 = New-ScheduledTaskTrigger -Daily -At "09:00AM"

$Settings1 = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

Register-ScheduledTask `
    -TaskName "career-ops-daily-scan" `
    -Description "매일 09:00 금융 채용 공고 자동 수집 (사람인+링커리어+원티드)" `
    -Action $Action1 `
    -Trigger $Trigger1 `
    -Settings $Settings1 `
    -RunLevel Highest `
    -Force

Write-Host "✓ Task 1 등록: career-ops-daily-scan (매일 09:00)" -ForegroundColor Green

# ── Task 2: 매주 월요일 09:30 전체 채널 풀스캔 ──────────────────────────────
$WeeklyScript = @"
cd '$ProjectDir'
`$env:PYTHONIOENCODING = 'utf-8'
uv run career-ops scan --all
uv run career-ops export --open-only -o `"`$env:USERPROFILE\Desktop\공고현황_주간풀스캔.xlsx`"
"@

$WeeklyScriptPath = "$ProjectDir\scripts\_weekly_full_scan.ps1"
$WeeklyScript | Out-File -FilePath $WeeklyScriptPath -Encoding UTF8 -Force

$Action2 = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$WeeklyScriptPath`""

$Trigger2 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At "09:30AM"

Register-ScheduledTask `
    -TaskName "career-ops-weekly-fullscan" `
    -Description "매주 월요일 09:30 전체 36채널 풀스캔" `
    -Action $Action2 `
    -Trigger $Trigger2 `
    -Settings $Settings1 `
    -RunLevel Highest `
    -Force

Write-Host "✓ Task 2 등록: career-ops-weekly-fullscan (매주 월요일 09:30)" -ForegroundColor Green

# ── Task 3: 매일 09:05 Obsidian vault-sync ──────────────────────────────────
$VaultScript = @"
cd '$ProjectDir'
`$env:PYTHONIOENCODING = 'utf-8'
uv run career-ops vault-sync --path `"`$env:USERPROFILE\obsidian-vault\career-ops`"
"@

$VaultScriptPath = "$ProjectDir\scripts\_vault_sync.ps1"
$VaultScript | Out-File -FilePath $VaultScriptPath -Encoding UTF8 -Force

$Action3 = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$VaultScriptPath`""

$Trigger3 = New-ScheduledTaskTrigger -Daily -At "09:05AM"

Register-ScheduledTask `
    -TaskName "career-ops-vault-sync" `
    -Description "매일 09:05 SQLite → Obsidian Vault 동기화" `
    -Action $Action3 `
    -Trigger $Trigger3 `
    -Settings $Settings1 `
    -RunLevel Highest `
    -Force

Write-Host "✓ Task 3 등록: career-ops-vault-sync (매일 09:05)" -ForegroundColor Green

Write-Host ""
Write-Host "등록된 태스크 목록:" -ForegroundColor Cyan
Get-ScheduledTask | Where-Object { $_.TaskName -like "career-ops-*" } | Format-Table TaskName, State
