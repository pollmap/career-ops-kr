$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir
$env:PYTHONIOENCODING = "utf-8"
$VaultDir = if ($env:CAREER_OPS_VAULT_DIR) { $env:CAREER_OPS_VAULT_DIR } else { "$env:USERPROFILE\obsidian-vault\career-ops" }

uv run career-ops vault-sync --path "$VaultDir"
