param([string]$act, [int]$x=0, [int]$y=0, [string]$text="", [string]$out="C:\HeroVerse\ui.png", [int]$wait=3, [switch]$nofocus)
# Robust focus (coordinator 2026-11-03): before every click, keystroke or scroll the ChatGPT window is found, restored if
# minimized, brought to the foreground (AttachThreadInput + SetForegroundWindow + BringWindowToTop + SetFocus) and verified with
# GetForegroundWindow, up to 3 tries. If it cannot be the foreground, NOTHING is clicked or typed (exit 9, "FOCUS_FAILED").
# lastact.txt holds the tick of this route's last action, so select_chat.ps1 can tell the owner's input from ours (E305).
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;using System.Text;
public class HVUI{
[DllImport("user32.dll")]public static extern bool SetCursorPos(int x,int y);
[DllImport("user32.dll")]public static extern void mouse_event(int f,int x,int y,int d,int e);
[DllImport("user32.dll")]public static extern IntPtr GetForegroundWindow();
[DllImport("user32.dll")]public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")]public static extern bool BringWindowToTop(IntPtr h);
[DllImport("user32.dll")]public static extern IntPtr SetFocus(IntPtr h);
[DllImport("user32.dll")]public static extern bool ShowWindow(IntPtr h,int c);
[DllImport("user32.dll")]public static extern bool IsIconic(IntPtr h);
[DllImport("user32.dll")]public static extern uint GetWindowThreadProcessId(IntPtr h,out uint p);
[DllImport("user32.dll")]public static extern bool AttachThreadInput(uint a,uint b,bool f);
[DllImport("kernel32.dll")]public static extern uint GetCurrentThreadId();
}
'@
function Get-HVWindow {
  $p = Get-Process -Name ChatGPT -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -like '*ChatGPT*' } | Select-Object -First 1
  if ($p) { return $p.MainWindowHandle }
  return [IntPtr]::Zero
}
function Test-HVFocus { $h = Get-HVWindow; return ($h -ne [IntPtr]::Zero -and [HVUI]::GetForegroundWindow() -eq $h) }
Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public class HVIdle{[StructLayout(LayoutKind.Sequential)]public struct L{public uint s;public uint t;}[DllImport("user32.dll")]public static extern bool GetLastInputInfo(ref L p);}'
# someone else is using the PC: the last system input is newer than the last action of this script, and less than 20 s old
function Test-HVOwnerBusy {
  $l = New-Object HVIdle+L; $l.s = 8; [HVIdle]::GetLastInputInfo([ref]$l) | Out-Null
  $now = [Environment]::TickCount; $mine = 0
  if (Test-Path 'C:\HeroVerse\lastact.txt') { $mine = [int64](Get-Content 'C:\HeroVerse\lastact.txt' -ErrorAction SilentlyContinue) }
  $lastInput = [int64]$l.t
  if ($lastInput -le $mine + 1500) { return $false }
  return (($now - $lastInput) -lt 20000)
}
function Set-HVFocus {
  if (-not (Test-HVFocus) -and (Test-HVOwnerBusy)) { return $false }
  for ($try = 0; $try -lt 3; $try++) {
    $h = Get-HVWindow
    if ($h -eq [IntPtr]::Zero) { Start-Process 'shell:AppsFolder\OpenAI.Codex_2p2nqsd0c76g0!App'; Start-Sleep 4; continue }
    if ([HVUI]::IsIconic($h)) { [HVUI]::ShowWindow($h, 9) | Out-Null; Start-Sleep -m 500 }
    $fg = [HVUI]::GetForegroundWindow(); $dummy = [uint32]0
    $fgThread = [HVUI]::GetWindowThreadProcessId($fg, [ref]$dummy); $me = [HVUI]::GetCurrentThreadId()
    $tgtThread = [HVUI]::GetWindowThreadProcessId($h, [ref]$dummy)
    [HVUI]::AttachThreadInput($me, $fgThread, $true) | Out-Null
    [HVUI]::AttachThreadInput($me, $tgtThread, $true) | Out-Null
    [HVUI]::BringWindowToTop($h) | Out-Null; [HVUI]::SetForegroundWindow($h) | Out-Null; [HVUI]::SetFocus($h) | Out-Null
    [HVUI]::AttachThreadInput($me, $fgThread, $false) | Out-Null
    [HVUI]::AttachThreadInput($me, $tgtThread, $false) | Out-Null
    Start-Sleep -m 700
    if (Test-HVFocus) { return $true }
  }
  return $false
}
if (-not $nofocus -and $act -in @('click', 'type', 'scroll')) {
  if (-not (Set-HVFocus)) { "FOCUS_FAILED"; exit 9 }
}
if ($act -eq "click") { [HVUI]::SetCursorPos($x,$y) | Out-Null; Start-Sleep -m 350; if (-not $nofocus -and -not (Test-HVFocus)) { "FOCUS_LOST"; exit 9 }; [HVUI]::mouse_event(2,0,0,0,0); Start-Sleep -m 80; [HVUI]::mouse_event(4,0,0,0,0) }
if ($act -eq "type") { if (-not $nofocus -and -not (Test-HVFocus)) { "FOCUS_LOST"; exit 9 }; [System.Windows.Forms.SendKeys]::SendWait($text) }
if ($act -eq "scroll") { [HVUI]::SetCursorPos($x,$y) | Out-Null; for($i=0;$i -lt 4;$i++){ if (-not $nofocus -and -not (Test-HVFocus)) { "FOCUS_LOST"; exit 9 }; [HVUI]::mouse_event(0x800,0,0,-120,0);Start-Sleep -m 200} }
Set-Content 'C:\HeroVerse\lastact.txt' ([Environment]::TickCount)
Start-Sleep $wait
Set-Content 'C:\HeroVerse\lastact.txt' ([Environment]::TickCount)
$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; $bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height; $g=[System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size); $bmp.Save($out); "ok"
