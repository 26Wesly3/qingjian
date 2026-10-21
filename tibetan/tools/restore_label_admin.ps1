# 右键“以管理员身份运行”：把设置程序还原成原版
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$bak = Join-Path $root 'backup\qingjian-settings.exe.orig'
$dst = 'C:\Program Files\Qingjian\qingjian-settings.exe'

if (-not (Test-Path $bak)) { throw "找不到备份：$bak" }
taskkill /IM qingjian-settings.exe /F 2>$null | Out-Null
Start-Sleep -Milliseconds 800
Copy-Item -LiteralPath $bak -Destination $dst -Force
Write-Host "已还原设置程序：$dst"
