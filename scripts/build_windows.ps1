$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if (Test-Path $venvPython) {
    $python = $venvPython
} else {
    $python = "python"
}

Write-Host "[INFO] Using Python: $python"

try {
    & $python -m PyInstaller --version | Out-Host
} catch {
    Write-Error "PyInstaller 未安装。请先在当前环境中安装后再执行打包。"
}

& $python -m PyInstaller "$projectRoot\quark_uploader.spec" --noconfirm
Write-Host "[INFO] 打包完成，请查看 dist 目录。"
