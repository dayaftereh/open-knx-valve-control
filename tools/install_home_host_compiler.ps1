# Reproducible, opt-in LLO Home native host compiler setup (KNX028).
# Install only into C:\_myspace\Tools; no PATH/registry/global Git modifications.
# Source: https://github.com/brechtsanders/winlibs_mingw/releases/tag/16.2.0posix-14.0.0-ucrt-r2
param(
    [string]$ToolsRoot = 'C:\_myspace\Tools'
)
$ErrorActionPreference = 'Stop'
$tag = '16.2.0posix-14.0.0-ucrt-r2'
$name = 'winlibs-x86_64-posix-seh-gcc-16.2.0-mingw-w64ucrt-14.0.0-r2.7z'
$base = "https://github.com/brechtsanders/winlibs_mingw/releases/download/$tag"
$archive = Join-Path $ToolsRoot $name
$install = Join-Path $ToolsRoot 'winlibs-gcc-16.2.0-ucrt'
$exe = Join-Path $install 'mingw64\bin\g++.exe'
$sevenZip = Join-Path $ToolsRoot '7-Zip\7z.exe'

if (Test-Path -LiteralPath $exe) {
    Write-Output "Already installed: $exe"
    & $exe --version
    exit $LASTEXITCODE
}
if (!(Test-Path -LiteralPath $sevenZip)) { throw "7-Zip missing: $sevenZip" }
if (Test-Path -LiteralPath $install) {
    throw "Partial/different compiler install found at $install; inspect before retrying"
}
New-Item -ItemType Directory -Path $ToolsRoot -Force | Out-Null
if (!(Test-Path -LiteralPath $archive)) {
    Write-Output "Downloading pinned host compiler: $name"
    Invoke-WebRequest -Uri "$base/$name" -OutFile $archive -UseBasicParsing -TimeoutSec 600
}
# Compare against checksum published with the same release.
$hashText = (Invoke-WebRequest -Uri "$base/$name.sha256" -UseBasicParsing -TimeoutSec 60).Content
if ($hashText -is [byte[]]) { $hashText = [Text.Encoding]::ASCII.GetString($hashText) }
$match = [regex]::Match([string]$hashText, '[a-fA-F0-9]{64}')
if (!$match.Success) { throw 'No SHA256 in upstream checksum sidecar' }
$actual = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
if ($actual -ine $match.Value) {
    throw "Downloaded archive SHA256 mismatch: got $actual"
}
Write-Output "SHA256 verified: $actual"
New-Item -ItemType Directory -Path $install | Out-Null
& $sevenZip x $archive ("-o$install") -y | Out-Null
if ($LASTEXITCODE -ne 0 -or !(Test-Path -LiteralPath $exe)) {
    throw "Native compiler extraction incomplete, inspect $install"
}
Write-Output "Installed native C++ host compiler: $exe"
& $exe --version
exit $LASTEXITCODE
