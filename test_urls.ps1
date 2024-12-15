# Test URLs for the goal bot
$urls = @(
    "1hf0otj", # Southampton vs Tottenham
    "1hf1pul", # Chelsea vs Brentford
    "1hex1o2", # Man City vs Man United
    "1he6l29"  # Wolves vs Ipswich
)

Write-Host "Testing URLs..." -ForegroundColor Green
Write-Host "----------------" -ForegroundColor Green

foreach ($url in $urls) {
    Write-Host "`nTesting thread: $url" -ForegroundColor Yellow
    python -m src.main --test-threads $url --ignore-posted --ignore-duplicates
    
    Write-Host "`nPress Enter to continue to next URL..." -ForegroundColor Cyan
    $null = Read-Host
}

Write-Host "`nAll tests complete!" -ForegroundColor Green
