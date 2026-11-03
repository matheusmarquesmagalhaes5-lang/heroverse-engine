# drive.ps1 -ids <ids> [-plan <plan id> -aspect 9:16 -branch <branch>]
# Legacy (no -plan): ids are flood-ends-long shot names without "s-" (still = flood-ends-long-s-<id>), 16:9.
# With -plan: ids are full shot ids (still = <plan>-<id>), aspect 16:9 or 9:16.
param([string[]]$ids, [string]$plan = '', [string]$aspect = '16:9', [string]$branch = 'claude/stoic-edison-gii4wc', [string]$run = '')
$log = 'C:\HeroVerse\log.txt'
foreach ($s in $ids) {
  $still = if ($plan) { "$plan-$s" } else { "flood-ends-long-s-$s" }
  $png = "C:\HeroVerse\gpt-images\$still.png"
  $good = $false
  for ($att = 0; $att -lt 2 -and -not $good; $att++) {
    "$(Get-Date -Format HH:mm:ss) START $still att=$att" | Add-Content $log
    & C:\HeroVerse\one2.ps1 -still $still -phase 0 -aspect $aspect -branch $branch -run $run | Add-Content $log
    Start-Sleep 140
    $dupe = $false
    for ($try = 0; $try -lt 3; $try++) {
      $out = & C:\HeroVerse\one2.ps1 -still $still -phase 1 -aspect $aspect -branch $branch -run $run
      if ("$out" -match 'DUPLICATE') { $dupe = $true; "$(Get-Date -Format HH:mm:ss) DUP $still" | Add-Content $log; break }
      if (Test-Path $png) { $good = $true; break }
      "$(Get-Date -Format HH:mm:ss) RETRY $still" | Add-Content $log
      Start-Sleep 40
    }
  }
  if (-not $good) {
    $n = & C:\HeroVerse\shot.ps1 -wait 1
    "$(Get-Date -Format HH:mm:ss) FAIL $still $n" | Add-Content $log
    exit 1
  }
  ($out | Out-String).Trim() | Add-Content $log
}
"$(Get-Date -Format HH:mm:ss) ALLDONE" | Add-Content $log
