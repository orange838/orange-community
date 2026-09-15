$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
node .\scripts\gather-cf-status.mjs
python -m http.server 8080
