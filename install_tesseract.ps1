$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$url = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
$installerPath = Join-Path $env:TEMP "tesseract_installer.exe"

Write-Host "Downloading Tesseract OCR Installer..."
Invoke-WebRequest -Uri $url -OutFile $installerPath

Write-Host "Download complete. Launching installer..."
Write-Host "A User Account Control (UAC) prompt will appear. Please click 'Yes' to allow the installation."

Start-Process -FilePath $installerPath -ArgumentList "/S" -Verb RunAs -Wait

Write-Host "Tesseract OCR has been installed successfully!"
