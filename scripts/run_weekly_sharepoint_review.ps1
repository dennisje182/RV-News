param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot "..\automation\config.json")
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Missing $ConfigPath. Copy automation\\config.example.json to config.json and set staging_drop to the synced SharePoint Incoming folder."
}

$config = Get-Content -LiteralPath $ConfigPath -Raw -Encoding utf8 | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace($config.staging_drop)) {
    throw "config.json requires staging_drop."
}

Push-Location $projectRoot
try {
    uv --system-certs run scripts/collect.py --days ([int]$config.source_days)
    if ($LASTEXITCODE -ne 0) { throw "Collection failed with exit code $LASTEXITCODE." }

    uv --system-certs run scripts/stage_weekly_review.py `
        --output $config.staging_drop `
        --max-input ([int]$config.max_input_articles) `
        --review-cards ([int]$config.review_cards)
    if ($LASTEXITCODE -ne 0) { throw "SharePoint staging failed with exit code $LASTEXITCODE." }
}
finally {
    Pop-Location
}
