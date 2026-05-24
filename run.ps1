param(
    [switch]$Demo,
    [switch]$SetupOnly
)
Set-Location $PSScriptRoot
$py = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }
$args = @("run.py")
if ($Demo) { $args += "--demo" }
if ($SetupOnly) { $args += "--setup-only" }
& $py @args
exit $LASTEXITCODE
