param([string]$still, [int]$phase = 0, [string]$aspect = '16:9', [string]$branch = 'claude/stoic-edison-gii4wc')
# phase 0 = send prompt in the single chat; phase 1 = download + save + upload candidate
$ui = 'C:\HeroVerse\ui.ps1'
$png = "C:\HeroVerse\gpt-images\$still.png"
Add-Type -Namespace W -Name U -MemberDefinition '[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern System.IntPtr GetForegroundWindow(); [System.Runtime.InteropServices.DllImport("user32.dll", CharSet=System.Runtime.InteropServices.CharSet.Unicode)] public static extern int GetWindowText(System.IntPtr h, System.Text.StringBuilder s, int n);'
if ($phase -eq 0) {
  if (Test-Path $png) { Remove-Item $png }
  & C:\HeroVerse\send2.ps1 -still $still -cy 675 -aspect $aspect -branch $branch
} else {
  & $ui -act scroll -x 700 -y 400 -wait 1 | Out-Null
  & $ui -act click -x 697 -y 398 -wait 3 | Out-Null
  & $ui -act click -x 859 -y 23 -wait 3 | Out-Null
  $ok = $false
  for ($i = 0; $i -lt 14; $i++) { $sb = New-Object System.Text.StringBuilder 256; [void][W.U]::GetWindowText([W.U]::GetForegroundWindow(), $sb, 256); if ($sb.ToString() -eq 'Salvar como') { $ok = $true; break }; Start-Sleep 2 }
  if (-not $ok) { & $ui -act type -text "{ESC}" -wait 1 | Out-Null; "NODIALOG $still"; exit 7 }
  & $ui -act type -text "$png~" -wait 4 | Out-Null
  & $ui -act type -text "{ESC}" -wait 2 | Out-Null
  & C:\HeroVerse\save.ps1 -still $still -sy 0 -aspect $aspect -branch $branch
}
