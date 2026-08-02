param(
    [string]$SshHost = $env:DISCLOSEAI_GPU_SSH_HOST,
    [string]$KeyPath = "$env:USERPROFILE\.ssh\discloseai_gpu_backup_ed25519",
    [string]$PidFile = "/data/discloseai/manifests/eqs_v3_batch_03.pid",
    [int]$PollSeconds = 60
)

$ErrorActionPreference = "Stop"

if (-not $SshHost) {
    throw "SshHost 미설정 — -SshHost 인자를 넘기거나 환경변수 DISCLOSEAI_GPU_SSH_HOST(예: user@host)를 설정하세요."
}

while ($true) {
    $remotePid = (ssh -i $KeyPath -o IdentitiesOnly=yes -o BatchMode=yes $SshHost "cat $PidFile" 2>$null).Trim()
    if (-not $remotePid) {
        break
    }

    ssh -i $KeyPath -o IdentitiesOnly=yes -o BatchMode=yes $SshHost "kill -0 $remotePid 2>/dev/null" 2>$null
    if ($LASTEXITCODE -ne 0) {
        break
    }
    Start-Sleep -Seconds $PollSeconds
}

[console]::Beep(880, 180)
Start-Sleep -Milliseconds 80
[console]::Beep(1175, 220)
Add-Type -AssemblyName PresentationFramework
[System.Windows.MessageBox]::Show(
    "EQS 3차 DART 수집 배치가 완료되었습니다. Codex에서 다음 상태를 확인하세요.",
    "DiscloseAI 수집 완료",
    "OK",
    "Information"
) | Out-Null
