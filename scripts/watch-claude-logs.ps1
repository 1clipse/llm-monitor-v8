param(
  [string]$ProjectsDir = "C:\Users\Knightz\.claude\projects",
  [string]$MonitorUrl = "http://127.0.0.1:8000/ingest",
  [int]$PollSeconds = 2,
  [string]$StateFile = "D:\LLMtext\llm-monitor-v8\data\claude-log-watcher-state.json"
)

$ErrorActionPreference = "Stop"

function Load-State {
  if (Test-Path $StateFile) {
    try {
      $raw = Get-Content $StateFile -Raw -Encoding utf8
      if ($raw.Trim()) {
        return $raw | ConvertFrom-Json -AsHashtable
      }
    } catch {
      Write-Warning "State file is unreadable; starting a fresh watcher state. $($_.Exception.Message)"
    }
  }
  return @{}
}

function Save-State($State) {
  $dir = Split-Path -Parent $StateFile
  if (-not (Test-Path $dir)) {
    New-Item -ItemType Directory -Force $dir | Out-Null
  }
  $State | ConvertTo-Json -Depth 8 | Set-Content -Path $StateFile -Encoding utf8
}

function Get-TextFromContent($Content) {
  $parts = New-Object System.Collections.Generic.List[string]

  if ($null -eq $Content) {
    return ""
  }

  if ($Content -is [string]) {
    return $Content.Trim()
  }

  foreach ($block in $Content) {
    if ($null -eq $block) {
      continue
    }

    if ($block -is [string]) {
      if ($block.Trim()) { $parts.Add($block.Trim()) }
      continue
    }

    $type = $block.type
    if ($type -eq "text" -and $block.text) {
      $text = [string]$block.text
      if ($text.Trim()) { $parts.Add($text.Trim()) }
    }
  }

  return ($parts -join "`n").Trim()
}

function Send-ToMonitor($Event, [string]$Text, [string]$FilePath) {
  $sessionId = [System.IO.Path]::GetFileNameWithoutExtension($FilePath)
  $maxTextLength = 190000
  if ($Text.Length -gt $maxTextLength) {
    $Text = $Text.Substring(0, $maxTextLength) + "`n`n[watcher: reply truncated before local analysis]"
  }

  $payload = @{
    relay = "cc-switch/claude-code"
    model = "cc-switch-observed"
    prompt = ""
    text = $Text
    metadata = @{
      source = "claude-jsonl-watcher"
      file = $FilePath
      uuid = $Event.uuid
      parent_uuid = $Event.parentUuid
      timestamp = $Event.timestamp
      session_id = $sessionId
    }
  }

  $json = $payload | ConvertTo-Json -Depth 12 -Compress
  $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($json)
  try {
    $result = Invoke-RestMethod -Uri $MonitorUrl -Method Post -ContentType "application/json; charset=utf-8" -Body $bodyBytes -TimeoutSec 8
    $risk = $result.analysis.risk_label
    $score = $result.analysis.risk_score
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] sent assistant reply from $sessionId risk=$risk score=$score"
  } catch {
    $details = $_.Exception.Message
    if ($_.Exception.Response) {
      try {
        $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
        $body = $reader.ReadToEnd()
        if ($body) { $details = "$details $body" }
      } catch {}
    }
    Write-Warning "Monitor post failed: $details"
  }
}

function Process-Line([string]$Line, [string]$FilePath) {
  if (-not $Line.Trim()) {
    return
  }

  try {
    $event = $Line | ConvertFrom-Json
  } catch {
    return
  }

  if ($event.type -ne "assistant") {
    return
  }

  if ($null -eq $event.message -or $event.message.role -ne "assistant") {
    return
  }

  $text = Get-TextFromContent $event.message.content
  if (-not $text) {
    return
  }

  Send-ToMonitor -Event $event -Text $text -FilePath $FilePath
}

function Get-LineCount([string]$Path) {
  try {
    return [int](Get-Content -Path $Path -Encoding utf8 | Measure-Object -Line).Lines
  } catch {
    return 0
  }
}

if (-not (Test-Path $ProjectsDir)) {
  throw "Claude projects directory not found: $ProjectsDir"
}

$state = Load-State
Write-Host "Watching Claude Code JSONL logs: $ProjectsDir"
Write-Host "Posting analyzed replies to: $MonitorUrl"
Write-Host "State file: $StateFile"
Write-Host "First-time files are initialized at end-of-file to avoid replaying old sessions."

while ($true) {
  $files = Get-ChildItem -Path $ProjectsDir -Recurse -Filter "*.jsonl" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 80

  foreach ($file in $files) {
    $path = $file.FullName
    $currentLineCount = Get-LineCount $path

    if (-not $state.ContainsKey($path)) {
      $state[$path] = $currentLineCount
      continue
    }

    $lastLine = [int]$state[$path]
    if ($currentLineCount -lt $lastLine) {
      $lastLine = 0
    }

    if ($currentLineCount -gt $lastLine) {
      $newCount = $currentLineCount - $lastLine
      try {
        $newLines = Get-Content -Path $path -Encoding utf8 -Tail $newCount
        foreach ($line in $newLines) {
          Process-Line -Line $line -FilePath $path
        }
      } catch {
        Write-Warning "Failed reading $path : $($_.Exception.Message)"
      }
      $state[$path] = $currentLineCount
    }
  }

  Save-State $state
  Start-Sleep -Seconds $PollSeconds
}
