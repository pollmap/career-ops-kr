# 스크립트 위치 기준 프로젝트 루트 찾기
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir
$env:PYTHONIOENCODING = "utf-8"

# 엑셀 출력 위치는 환경변수 CAREER_OPS_EXPORT_DIR (기본: 사용자 Desktop)
$ExportDir = if ($env:CAREER_OPS_EXPORT_DIR) { $env:CAREER_OPS_EXPORT_DIR } else { "$env:USERPROFILE\Desktop" }

uv run career-ops scan --site linkareer
uv run career-ops scan --site saramin
uv run career-ops scan --site wanted
uv run career-ops export --open-only -o "$ExportDir\공고현황_최신.xlsx"
