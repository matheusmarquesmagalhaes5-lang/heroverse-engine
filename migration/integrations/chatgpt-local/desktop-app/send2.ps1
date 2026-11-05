param([string]$still,[int]$cy=324,[string]$aspect='16:9',[string]$branch='claude/stoic-edison-gii4wc',[string]$run='')
# E305 (owner 2026-11-05): a still went to the WRONG chat because this script pasted and pressed Enter without knowing
# which conversation was open. The prompt is now put on the clipboard only after select_chat.ps1 has opened and verified
# the one chat "HeroVerse - stills" (OK), and Enter is pressed only after a second verification. Anything else stops here.
$ui = "C:\HeroVerse\ui.ps1"
$guard = "C:\HeroVerse\select_chat.ps1"
$rec = gh api "repos/matheusmagah-cpu/heroverse-engine/contents/migration/production/bible/stills/$still.json?ref=$branch" -H "Accept: application/vnd.github.raw" | ConvertFrom-Json
$shape = if ($aspect -eq '9:16') { '9:16 vertical portrait' } else { '16:9 landscape' }
$prompt = "Create an image, $shape, no text. " + $rec.prompt.Replace("'", [string][char]0x2019)
$g = & $guard
$code = $LASTEXITCODE; $last = "$($g | Select-Object -Last 1)"
if ($code -ne 0 -or $last -ne 'OK') { "$last $still (nothing sent)"; exit $(if ($code) { $code } else { 4 }) }
Set-Clipboard $prompt
& $ui -act click -x 760 -y $cy -wait 1 | Out-Null
& $ui -act type -text "^a" -wait 1 | Out-Null; & $ui -act type -text "^v" -wait 2 | Out-Null
Set-Clipboard " "
$g = & $guard -verifyOnly
$code = $LASTEXITCODE; $last = "$($g | Select-Object -Last 1)"
if ($code -ne 0 -or $last -ne 'OK') {
  # the draft is left unsent and untouched (no keystroke into a conversation that is not verified)
  "$last $still (pasted, not sent)"; exit $(if ($code) { $code } else { 4 })
}
& $ui -act type -text "~" -wait 3 | Out-Null
"SENT $still"
