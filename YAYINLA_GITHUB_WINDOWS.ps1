param(
    [string]$Repository = "alarslan12/alfa-erp",
    [string]$ReleaseVersion = "v6.1.2"
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Set-Location -LiteralPath $PSScriptRoot

function Tool([string]$name, [string]$wingetId, [string[]]$locations) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($path in $locations) { if ($path -and (Test-Path -LiteralPath $path)) { return $path } }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "$name kurulu degil ve winget bulunamadi."
    }
    Write-Host "$name otomatik kuruluyor..."
    # PowerShell captures native stdout from functions: discard winget progress.
    # Only a single executable path may be emitted by this function.
    & winget install -e --id $wingetId --silent --accept-package-agreements --accept-source-agreements | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "$name kurulumu basarisiz." }
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($path in $locations) { if ($path -and (Test-Path -LiteralPath $path)) { return $path } }
    throw "$name bulunamadi. Windows oturumunu yeniden acip bu dosyayi tekrar calistirin."
}

function Exec([string]$bin, [string[]]$argsList) {
    & $bin @argsList
    if ($LASTEXITCODE -ne 0) { throw "Komut basarisiz oldu: $bin $($argsList -join ' ')" }
}

# Native commands used as checks intentionally return non-zero status.
# Windows PowerShell 5.1 can treat stderr as a terminating error with Stop.
# Disable that behavior ONLY for these checks, preserving the exit code.
function ProbeNative([string]$bin, [string[]]$argsList) {
    $prior = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $bin @argsList 2>$null | Out-Null
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prior
    }
}

$git = Tool "git.exe" "Git.Git" @("$env:ProgramFiles\Git\cmd\git.exe", "${env:ProgramFiles(x86)}\Git\cmd\git.exe")
if (-not (Test-Path -LiteralPath $git)) { throw "Git bulunamadi: $git" }
$gh = Tool "gh.exe" "GitHub.cli" @("$env:ProgramFiles\GitHub CLI\gh.exe", "$env:LOCALAPPDATA\Programs\GitHub CLI\gh.exe")
if (-not (Test-Path -LiteralPath $gh)) { throw "GitHub CLI bulunamadi: $gh" }

# Browser sign-in is the only unavoidable one-time interaction.
$authExitCode = ProbeNative $gh @('auth','status')
if ($authExitCode -ne 0) {
    Write-Host "GitHub hesabini tarayicidan bir kez baglayin..."
    Exec $gh @('auth','login','--hostname','github.com','--web','--git-protocol','https')
}
Exec $gh @('auth','setup-git')
Write-Host "Hedef depo: $Repository"
Exec $gh @('repo','view',$Repository,'--json','nameWithOwner,visibility')

# Do not publish any enrollment tokens or per-device files.
foreach ($forbidden in @('kurulum_bilgisi.json','.env','alfa_cihaz.bin','alfa_outbox.json')) {
    if (Test-Path -LiteralPath (Join-Path $PSScriptRoot $forbidden)) {
        throw "Guvenlik: $forbidden klasorde bulundu; once bu dosyayi proje disina tasiyin."
    }
}
if (-not (Test-Path '.github\workflows\build-windows.yml')) {
    throw 'GitHub Windows derleme is akisi bulunamadi.'
}
if (-not (Test-Path '.git')) {
    Exec $git @('init','-b','main')
}
Exec $git @('config','user.name','ALFA ERP Release')
Exec $git @('config','user.email','124261255+alarslan12@users.noreply.github.com')
$remoteExitCode = ProbeNative $git @('remote','get-url','origin')
if ($remoteExitCode -ne 0) {
    Exec $git @('remote','add','origin',"https://github.com/$Repository.git")
} else {
    $remote = (& $git remote get-url origin).Trim()
    if ($remote -notmatch [regex]::Escape($Repository)) {
        throw "Farkli bir GitHub reposu tanimli: $remote"
    }
}

Exec $git @('add','--all')
$diffExitCode = ProbeNative $git @('diff','--cached','--quiet')
if ($diffExitCode -ne 0) {
    Exec $git @('commit','-m',"release: ALFA ERP $ReleaseVersion Windows CI baseline")
} else {
    Write-Host 'Degisiklik yok, mevcut commit kullaniliyor.'
}
Exec $git @('branch','-M','main')

# GitHub repository was initialized independently with a README commit.
# Reconcile the histories without using force push or discarding remote commits.
Write-Host 'GitHub deposundaki son degisiklikler aliniyor...'
Exec $git @('fetch','origin','main')
$alreadyContainsRemote = ProbeNative $git @('merge-base','--is-ancestor','origin/main','HEAD')
if ($alreadyContainsRemote -ne 0) {
    Write-Host 'GitHub ilk commit ile yerel proje gecmisi guvenle birlestiriliyor...'
    # -X ours keeps the local version of conflicting text, including README;
    # non-conflicting remote files are preserved. Remote history stays intact.
    Exec $git @('merge','--allow-unrelated-histories','-X','ours','--no-edit','origin/main')
}
Write-Host 'Proje GitHub main dalina yukleniyor...'
Exec $git @('push','-u','origin','main')

# A tag builds both native Windows installers, once per release.
$tagExitCode = ProbeNative $git @('rev-parse','-q','--verify',"refs/tags/$ReleaseVersion")
if ($tagExitCode -ne 0) {
    Exec $git @('tag','-a',$ReleaseVersion,'-m',"ALFA ERP $ReleaseVersion stable candidate")
}
Write-Host 'Surüm etiketi GitHub Actions Windows derlemesini baslatacak...'
Exec $git @('push','origin',$ReleaseVersion)

Write-Host 'Windows testleri ve derleme GitHub Actions tarafinda izleniyor.'
$runId = $null
for ($i=0; $i -lt 24; $i++) {
    $runsJson = & $gh run list --repo $Repository --workflow build-windows.yml --limit 15 --json databaseId,headBranch,headSha,event,createdAt,status
    if ($LASTEXITCODE -eq 0 -and $runsJson) {
        $runs = $runsJson | ConvertFrom-Json
        $match = $runs | Where-Object { $_.headBranch -eq $ReleaseVersion -or $_.event -eq 'push' -and $_.headBranch -eq $ReleaseVersion } |
            Select-Object -First 1
        if ($match) { $runId = $match.databaseId; break }
    }
    Start-Sleep -Seconds 5
}
if (-not $runId) {
    Write-Host "Run algilanamadi. Actions sayfasini acin: https://github.com/$Repository/actions"
    exit 2
}
Exec $gh @('run','watch',"$runId",'--repo',$Repository,'--exit-status')
$downloadRoot = Join-Path $PSScriptRoot "WINDOWS_KURULUM_DOSYALARI"
New-Item -Path $downloadRoot -ItemType Directory -Force | Out-Null
Exec $gh @('run','download',"$runId",'--repo',$Repository,'--dir',$downloadRoot)
Write-Host "BASARILI. Iki Setup.exe dosyasi: $downloadRoot"
Start-Process explorer.exe $downloadRoot
