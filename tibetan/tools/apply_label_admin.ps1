# 右键“以管理员身份运行”：用补丁版替换青简设置程序，让“学习语言”下拉显示“藏文”
# 原程序备份到 tibetan/backup/qingjian-settings.exe.orig
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root 'dist\qingjian-settings-vi-tibetan.exe'
$dst = 'C:\Program Files\Qingjian\qingjian-settings.exe'
$bak = Join-Path $root 'backup\qingjian-settings.exe.orig'

if (-not (Test-Path $src)) { throw "找不到补丁文件：$src（先运行 python tools/patch_settings_label.py）" }
New-Item -ItemType Directory -Force (Join-Path $root 'backup') | Out-Null
if (-not (Test-Path $bak)) { Copy-Item -LiteralPath $dst -Destination $bak -Force }
taskkill /IM qingjian-settings.exe /F 2>$null | Out-Null
Start-Sleep -Milliseconds 800
Copy-Item -LiteralPath $src -Destination $dst -Force
Write-Host "已替换设置程序；备份：$bak"
