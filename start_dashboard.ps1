$workdir = $PSScriptRoot
$pythonExe = "C:\Program Files\Python312\python.exe"
$stdout = Join-Path $workdir "dashboard.out.log"
$stderr = Join-Path $workdir "dashboard.err.log"

Set-Location $workdir

if (Test-Path $stdout) {
    Remove-Item $stdout -Force
}

if (Test-Path $stderr) {
    Remove-Item $stderr -Force
}

Start-Process -FilePath $pythonExe `
    -ArgumentList @(
        "coin_recommendation_dashboard.py",
        "--config",
        "dashboard_runtime_config.json",
        "--host",
        "127.0.0.1",
        "--port",
        "8011",
        "--interval-seconds",
        "3600"
    ) `
    -WorkingDirectory $workdir `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr
