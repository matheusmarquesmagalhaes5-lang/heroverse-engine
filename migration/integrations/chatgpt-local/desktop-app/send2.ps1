param([string]$still,[int]$cy=324,[string]$aspect='16:9',[string]$branch='claude/stoic-edison-gii4wc')
$ui = "C:\HeroVerse\ui.ps1"
$rec = gh api "repos/matheusmagah-cpu/heroverse-engine/contents/migration/production/bible/stills/$still.json?ref=$branch" -H "Accept: application/vnd.github.raw" | ConvertFrom-Json
$shape = if ($aspect -eq '9:16') { '9:16 vertical portrait' } else { '16:9 landscape' }
$prompt = "Create an image, $shape, no text. " + $rec.prompt.Replace("'", [string][char]0x2019)
Set-Clipboard $prompt
& $ui -act click -x 760 -y $cy -wait 1 | Out-Null
& $ui -act type -text "^a" -wait 1 | Out-Null; & $ui -act type -text "^v" -wait 2 | Out-Null
& $ui -act type -text "~" -wait 3 | Out-Null
Set-Clipboard " "
"SENT $still"
