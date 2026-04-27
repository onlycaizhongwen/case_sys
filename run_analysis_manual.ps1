$workdir = $PSScriptRoot
$pythonExe = "C:\Program Files\Python312\python.exe"
$stdout = Join-Path $workdir "manual.out.log"
$stderr = Join-Path $workdir "manual.err.log"

Set-Location $workdir

if (Test-Path $stdout) {
    Remove-Item $stdout -Force
}

if (Test-Path $stderr) {
    Remove-Item $stderr -Force
}

Start-Process -FilePath $pythonExe `
    -ArgumentList @(
        "binance_day_contract_realtime_v5.py"
    ) `
    -WorkingDirectory $workdir `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -Wait `
    -NoNewWindow
