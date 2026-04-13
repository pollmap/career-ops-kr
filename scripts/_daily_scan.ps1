Set-Location "C:\Users\lch68\Desktop\05_개발·도구\career-ops-kr"
$env:PYTHONIOENCODING="utf-8"
uv run career-ops scan --site linkareer
uv run career-ops scan --site saramin
uv run career-ops scan --site wanted
uv run career-ops export --open-only -o C:\Users\lch68\Desktop\공고현황_최신.xlsx
