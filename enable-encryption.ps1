$buckets = @(
    "youtube-automation-audio-files",
    "youtube-automation-images",
    "youtube-automation-final-videos",
    "youtube-automation-data-grucia"
)

foreach ($bucket in $buckets) {
    Write-Host "Encrypting $bucket..." -ForegroundColor Cyan
    aws s3api put-bucket-encryption `
        --bucket $bucket `
        --server-side-encryption-configuration file://E:/youtube-content-automation/s3-encryption-config.json `
        --region eu-central-1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  SUCCESS" -ForegroundColor Green
    }
}
Write-Host "`nAll buckets encrypted!" -ForegroundColor Green
