Write-Host "Running all tests..." -ForegroundColor Cyan

# Activate virtual environment if it exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}

# Run pytest with coverage
Write-Host "`nRunning pytest with coverage..." -ForegroundColor Yellow
pytest --cov=src --cov-report=term-missing -v

# Show test summary
Write-Host "`nTest Summary:" -ForegroundColor Green
Write-Host "============" -ForegroundColor Green

# Get test files
$testFiles = Get-ChildItem -Path "tests" -Filter "test_*.py"
Write-Host "`nTest Files:" -ForegroundColor Cyan
foreach ($file in $testFiles) {
    Write-Host "- $($file.Name)"
}

Write-Host "`nDone!" -ForegroundColor Green

# Keep terminal open
Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
