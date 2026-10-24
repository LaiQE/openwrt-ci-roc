[CmdletBinding()]
param(
    [ValidateSet('Prepare', 'Config', 'Download', 'Build', 'Status', 'Logs', 'Export', 'Shell')]
    [string]$Stage = 'Build',
    [ValidateRange(1, 64)][int]$Jobs = 4,
    [string]$Container = 'openwrt-arthur-builder',
    [string]$Volume = 'openwrt-arthur-work',
    [switch]$Detach
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$image = 'localhost/openwrt-arthur-builder:24.04'

function Invoke-Podman {
    & podman @args
    if ($LASTEXITCODE -ne 0) { throw "Podman failed (exit $LASTEXITCODE): $args" }
}

Push-Location $repoRoot
try {
    if ($Stage -eq 'Status') {
        Invoke-Podman ps -a --filter "name=^${Container}$"
        Invoke-Podman top $Container
        Invoke-Podman exec $Container bash -c 'cat /work/status 2>/dev/null || true; df -h /work'
        return
    }
    if ($Stage -eq 'Logs') {
        Invoke-Podman exec $Container bash -c 'tail -n 60 /work/logs/*.log'
        return
    }
    if ($Stage -eq 'Export') {
        New-Item -ItemType Directory -Force artifacts | Out-Null
        New-Item -ItemType Directory -Force artifacts/logs | Out-Null
        Invoke-Podman cp "${Container}:/work/artifacts/." (Join-Path $repoRoot 'artifacts')
        Invoke-Podman cp "${Container}:/work/logs/." (Join-Path $repoRoot 'artifacts/logs')
        return
    }
    & podman container exists $Container
    if ($LASTEXITCODE -eq 1) {
        Invoke-Podman build -t $image -f Containerfile .
        Invoke-Podman volume create $Volume
        Invoke-Podman run --rm --user root --volume "${Volume}:/work" $image chown builder:builder /work
        Invoke-Podman run -d --name $Container --volume "${Volume}:/work" $image
    } elseif ($LASTEXITCODE -ne 0) {
        throw 'Unable to inspect the Podman container'
    } else {
        Invoke-Podman start $Container
    }
    if ($Stage -eq 'Shell') {
        Invoke-Podman exec -it $Container bash
        return
    }
    # Keep source/build trees on Linux ext4, and copy only the small configuration inputs.
    Invoke-Podman exec --user root $Container chown -R builder:builder /workspace
    foreach ($directory in @('configs', 'scripts', 'files', 'package', 'tests')) {
        Invoke-Podman cp (Join-Path $repoRoot "$directory/.") "${Container}:/workspace/$directory"
    }
    Invoke-Podman exec --user root $Container chown -R builder:builder /workspace
    $execArguments = @('exec')
    if ($Detach) { $execArguments += '-d' }
    $execArguments += @('--env', "JOBS=$Jobs", $Container, 'bash', '/workspace/scripts/local-build.sh', $Stage.ToLowerInvariant())
    Invoke-Podman @execArguments
    if ($Detach) { Write-Output "Started $Stage. Use -Stage Logs and -Stage Status to follow progress." }
} finally {
    Pop-Location
}
