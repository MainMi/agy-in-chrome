param (
    [Parameter(Mandatory=$false)]
    [string]$ExtensionId
)

$HostName = "com.antigravity.agy_in_chrome"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HostDir = Join-Path $ScriptDir "host"
$WrapperBat = Join-Path $HostDir "native-host-wrapper.bat"
$ManifestFile = Join-Path $HostDir "$HostName.json"

if (-not $ExtensionId) {
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host "  AGY in Chrome - Native Messaging Host Setup" -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Open chrome://extensions in your Chrome browser"
    Write-Host "2. Enable 'Developer mode' (top right)"
    Write-Host "3. Click 'Load unpacked' and select:"
    Write-Host "   $ScriptDir\extension" -ForegroundColor Yellow
    Write-Host "4. Copy the generated Extension ID"
    Write-Host ""
    $ExtensionId = Read-Host "Paste the Extension ID here"
}

$ExtensionId = $ExtensionId.Trim()

if (-not $ExtensionId) {
    Write-Error "Extension ID cannot be empty."
    exit 1
}

# Create wrapper bat if missing
$NodePath = (Get-Command node -ErrorAction SilentlyContinue).Source
if (-not $NodePath) {
    $NodePath = "C:\Program Files\nodejs\node.exe"
}
$NativeHostJs = Join-Path $HostDir "native-host.js"
$BatContent = "@echo off`r`n`"$NodePath`" `"$NativeHostJs`" %*`r`n"
Set-Content -Path $WrapperBat -Value $BatContent -NoNewline -Encoding ASCII

# Escape backslashes for JSON
$EscapedWrapper = $WrapperBat.Replace("\", "\\")

# Generate JSON manifest
$ManifestContent = @"
{
  "name": "$HostName",
  "description": "AGY in Chrome Native Messaging Host",
  "path": "$EscapedWrapper",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://$ExtensionId/"
  ]
}
"@

Set-Content -Path $ManifestFile -Value $ManifestContent -Encoding UTF8
Write-Host "Manifest created: $ManifestFile" -ForegroundColor Green

# Register in Windows Registry (HKCU - no admin required)
$RegTargets = @(
    "HKCU:\Software\Google\Chrome\NativeMessagingHosts\$HostName",
    "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\$HostName",
    "HKCU:\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\$HostName"
)

foreach ($regPath in $RegTargets) {
    try {
        New-Item -Path $regPath -Force | Out-Null
        Set-ItemProperty -Path $regPath -Name "(Default)" -Value $ManifestFile
        Write-Host "Registered in registry: $regPath" -ForegroundColor Green
    } catch {
        # Ignore if browser hive does not exist
    }
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Setup complete! Host registered for AGY." -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To add this MCP server to AGY, configure:"
Write-Host @"
`"mcpServers`": {
  `"agy-in-chrome`": {
    `"command`": `"$($NodePath.Replace('\', '\\'))`",
    `"args`": [`"$($((Join-Path $HostDir 'mcp-server.js')).Replace('\', '\\'))`"]
  }
}
"@ -ForegroundColor Yellow
