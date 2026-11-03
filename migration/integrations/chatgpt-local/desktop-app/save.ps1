param([string]$still, [int]$sy = 504, [string]$aspect = '16:9', [string]$branch = 'claude/stoic-edison-gii4wc', [string]$run = '')
$ui = 'C:\HeroVerse\ui.ps1'
$png = "C:\HeroVerse\gpt-images\$still.png"
if (-not $run) { $run = if ($aspect -eq '9:16') { '2026110301' } else { '2026110101' } }
$cand = "$still-$run-1"
$jpg = "C:\HeroVerse\gpt-images\$cand.jpg"
if ($sy -gt 0) {
  & $ui -act click -x 906 -y $sy -wait 2 | Out-Null
  & $ui -act click -x 891 -y 590 -wait 7 | Out-Null
  & $ui -act type -text "$png~" -wait 3 | Out-Null
  & $ui -act click -x 975 -y 87 -wait 1 | Out-Null
}
if (-not (Test-Path $png)) { "NO_IMAGE $still"; exit 6 }
$h0 = (Get-FileHash $png -Algorithm SHA256).Hash; $dup = Get-ChildItem C:\HeroVerse\gpt-images\*.png | ? { $_.FullName -ne $png -and (Get-FileHash $_.FullName -Algorithm SHA256).Hash -eq $h0 }; if ($dup) { Remove-Item $png; "DUPLICATE $still"; exit 8 }
Add-Type -AssemblyName System.Drawing
$src = [System.Drawing.Image]::FromFile($png)
$w = $src.Width; $h = $src.Height
if ($aspect -eq '9:16') { $tw = 1080; $th = 1920 } else { $tw = 1920; $th = 1080 }
# centre crop of the source to the target aspect, then resize (no stretching)
$sw = [double]$w; $sh = [double]$h
if (($sw / $sh) -gt ($tw / $th)) { $cw = $sh * $tw / $th; $ch = $sh } else { $cw = $sw; $ch = $sw * $th / $tw }
$cx = ($sw - $cw) / 2; $cy = ($sh - $ch) / 2
$bmp = New-Object System.Drawing.Bitmap $tw, $th
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.InterpolationMode = 'HighQualityBicubic'; $g.SmoothingMode = 'HighQuality'; $g.PixelOffsetMode = 'HighQuality'
$dst = New-Object System.Drawing.Rectangle 0, 0, $tw, $th
$g.DrawImage($src, $dst, [int]$cx, [int]$cy, [int]$cw, [int]$ch, [System.Drawing.GraphicsUnit]::Pixel)
$enc = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object { $_.MimeType -eq 'image/jpeg' }
$ep = New-Object System.Drawing.Imaging.EncoderParameters 1
$ep.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality), 93L
$bmp.Save($jpg, $enc, $ep); $g.Dispose(); $bmp.Dispose(); $src.Dispose()
$pngsha = (Get-FileHash $png -Algorithm SHA256).Hash.ToLower()
$pngsize = (Get-Item $png).Length
$path = "migration/production/bible/stills/candidates/$cand.jpg"
$body = @{ message = "ChatGPT desktop candidate $cand (DRAFT for the still review)"; branch = $branch; content = [Convert]::ToBase64String([IO.File]::ReadAllBytes($jpg)) } | ConvertTo-Json -Compress
$tmp = "C:\HeroVerse\gpt-images\put.json"
[IO.File]::WriteAllText($tmp, $body)
gh api -X PUT "repos/matheusmagah-cpu/heroverse-engine/contents/$path" --input $tmp --jq '.commit.sha' | Out-Null
"DONE $still png_sha256=$pngsha png_size=$pngsize w=$w h=$h"
