$buckets = @(
    "youtube-automation-audio-files",
    "youtube-automation-images",
    "youtube-automation-final-videos",
    "youtube-automation-data-grucia"
)

foreach ($bucket in $buckets) {
    Write-Host "`n=== Processing bucket: $bucket ===" -ForegroundColor Cyan

    # 1. Enable Versioning
    Write-Host "  1/2 Enabling versioning..." -ForegroundColor Yellow
    aws s3api put-bucket-versioning `
        --bucket $bucket `
        --versioning-configuration Status=Enabled `
        --region eu-central-1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "    SUCCESS: Versioning enabled" -ForegroundColor Green
    } else {
        Write-Host "    ERROR: Versioning failed" -ForegroundColor Red
    }

    # 2. Enable Encryption (SSE-S3)
    Write-Host "  2/2 Enabling encryption..." -ForegroundColor Yellow
    aws s3api put-bucket-encryption `
        --bucket $bucket `
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                },
                "BucketKeyEnabled": true
            }]
        }' `
        --region eu-central-1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "    SUCCESS: Encryption enabled (AES256)" -ForegroundColor Green
    } else {
        Write-Host "    ERROR: Encryption failed" -ForegroundColor Red
    }
}

Write-Host "`n=== All buckets secured! ===" -ForegroundColor Green
Write-Host "Versioning: ENABLED (protection from overwrites)" -ForegroundColor White
Write-Host "Encryption: ENABLED (AES256 at rest)" -ForegroundColor White
