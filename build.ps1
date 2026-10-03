$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
& '.\.venv\Scripts\python.exe' 'tools\build_native.py'
if ($LASTEXITCODE -ne 0) { throw 'Falló la compilación nativa' }
