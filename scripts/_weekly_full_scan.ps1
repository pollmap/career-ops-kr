Set-Location "C:\Users\lch68\Desktop\05_개발·도구\career-ops-kr"
$env:PYTHONIOENCODING="utf-8"
uv run career-ops scan --all
uv run career-ops export --open-only -o C:\Users\lch68\Desktop\공고현황_주간풀스캔.xlsx
