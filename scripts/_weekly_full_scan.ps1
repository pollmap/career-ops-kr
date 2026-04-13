$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir
$env:PYTHONIOENCODING = "utf-8"
$ExportDir = if ($env:CAREER_OPS_EXPORT_DIR) { $env:CAREER_OPS_EXPORT_DIR } else { "$env:USERPROFILE\Desktop" }

uv run career-ops scan --all
uv run career-ops export --open-only -o "$ExportDir\공고현황_주간풀스캔.xlsx"
