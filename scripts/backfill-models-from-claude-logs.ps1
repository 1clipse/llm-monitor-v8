param(
  [string]$ProjectsDir = "C:\Users\Knightz\.claude\projects",
  [string]$DatabasePath = "D:\LLMtext\llm-monitor-v8\data\llm_monitor.db",
  [int]$RecentFiles = 120
)

$ErrorActionPreference = "Stop"

function Get-TextFromContent($Content) {
  $parts = New-Object System.Collections.Generic.List[string]
  if ($null -eq $Content) { return "" }
  if ($Content -is [string]) { return $Content.Trim() }
  foreach ($block in $Content) {
    if ($null -eq $block) { continue }
    if ($block -is [string]) {
      if ($block.Trim()) { $parts.Add($block.Trim()) }
      continue
    }
    if ($block.type -eq "text" -and $block.text) {
      $text = [string]$block.text
      if ($text.Trim()) { $parts.Add($text.Trim()) }
    }
  }
  return ($parts -join "`n").Trim()
}

if (-not (Test-Path $ProjectsDir)) { throw "Claude projects directory not found: $ProjectsDir" }
if (-not (Test-Path $DatabasePath)) { throw "Monitor database not found: $DatabasePath" }

$events = New-Object System.Collections.Generic.List[object]
$files = Get-ChildItem -Path $ProjectsDir -Recurse -Filter "*.jsonl" -File -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTimeUtc -Descending |
  Select-Object -First $RecentFiles

foreach ($file in $files) {
  foreach ($line in Get-Content -Path $file.FullName -Encoding utf8) {
    if (-not $line.Trim()) { continue }
    try { $event = $line | ConvertFrom-Json } catch { continue }
    if ($event.type -ne "assistant" -or $null -eq $event.message -or $event.message.role -ne "assistant") { continue }
    $model = [string]$event.message.model
    if (-not $model) { continue }
    $text = Get-TextFromContent $event.message.content
    if (-not $text) { continue }
    $inputTokens = 0
    $outputTokens = 0
    if ($event.message.usage) {
      if ($null -ne $event.message.usage.input_tokens) { $inputTokens = [int]$event.message.usage.input_tokens }
      if ($null -ne $event.message.usage.output_tokens) { $outputTokens = [int]$event.message.usage.output_tokens }
    }
    $events.Add([pscustomobject]@{
      Model = $model
      Text = $text
      InputTokens = $inputTokens
      OutputTokens = $outputTokens
      TotalTokens = $inputTokens + $outputTokens
    })
  }
}

Add-Type -AssemblyName System.Data
$connection = [System.Data.SQLite.SQLiteConnection]::new("Data Source=$DatabasePath")
$connection.Open()
try {
  $updated = 0
  foreach ($event in $events) {
    $cmd = $connection.CreateCommand()
    $cmd.CommandText = @"
UPDATE logs
SET model_name = @model,
    provider = coalesce(provider, 'claude-code'),
    prompt_tokens = CASE WHEN @input_tokens > 0 THEN @input_tokens ELSE prompt_tokens END,
    completion_tokens = CASE WHEN @output_tokens > 0 THEN @output_tokens ELSE completion_tokens END,
    total_tokens = CASE WHEN @total_tokens > 0 THEN @total_tokens ELSE total_tokens END,
    token_source = CASE WHEN @total_tokens > 0 THEN 'reported' ELSE coalesce(token_source, 'estimated') END
WHERE id = (
  SELECT id FROM logs
  WHERE (model_name IS NULL OR model_name IN ('unknown-model', 'cc-switch-observed'))
    AND response_text = @text
  ORDER BY id DESC
  LIMIT 1
)
"@
    $null = $cmd.Parameters.AddWithValue('@model', $event.Model)
    $null = $cmd.Parameters.AddWithValue('@input_tokens', $event.InputTokens)
    $null = $cmd.Parameters.AddWithValue('@output_tokens', $event.OutputTokens)
    $null = $cmd.Parameters.AddWithValue('@total_tokens', $event.TotalTokens)
    $null = $cmd.Parameters.AddWithValue('@text', $event.Text)
    $updated += $cmd.ExecuteNonQuery()
  }
  Write-Host "Backfill complete. Matched/updated rows: $updated from Claude assistant events: $($events.Count)"
} finally {
  $connection.Close()
}
