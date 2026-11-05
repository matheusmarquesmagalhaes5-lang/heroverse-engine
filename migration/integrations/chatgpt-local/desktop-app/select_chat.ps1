param([switch]$verifyOnly, [switch]$viaSearch, [int]$idle = 120)
# select_chat.ps1 (E305, owner 2026-11-05): every still prompt goes to the ONE chat "HeroVerse - stills" (hyphen, en dash
# or em dash), and that chat is identified BEFORE anything is pasted or sent.
#   1. OWNER_ACTIVE (exit 3) when the PC had input in the last $idle seconds that this route did not make
#      (GetLastInputInfo against ui.ps1's lastact.txt). Nothing is clicked, typed or invoked.
#   2. Unless -verifyOnly: open the exact-named chat with a UIA Invoke on its sidebar button; when the sidebar does not
#      hold it (virtualized list), the app's own search palette (Ctrl+K) is opened, 'stills' is typed into its NEW search
#      box and the one exact-named result row is invoked. Enter is never pressed, and a new chat is never created.
#   3. Verify (signals): the page document is named exactly the stills chat; the sidebar button is the selected row or
#      the conversation header shows that name; and the open conversation (outside every input box) holds this project's
#      prompt marker. Any failure is WRONG_CHAT (exit 4) and nothing is sent.
# PRIVACY: the owner's other conversations are never printed, logged or copied: only the stills name, booleans and counts.
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
Add-Type -TypeDefinition @'
using System;using System.Runtime.InteropServices;
public class HVGuard{
[StructLayout(LayoutKind.Sequential)]public struct LII{public uint cbSize;public uint dwTime;}
[DllImport("user32.dll")]static extern bool GetLastInputInfo(ref LII p);
public static double IdleSeconds(){LII l=new LII();l.cbSize=(uint)Marshal.SizeOf(l);GetLastInputInfo(ref l);return unchecked((uint)Environment.TickCount-l.dwTime)/1000.0;}
public static double SinceTick(long t){return unchecked((uint)Environment.TickCount-(uint)(int)t)/1000.0;}
}
'@
$A = [System.Windows.Automation.AutomationElement]
$TS = [System.Windows.Automation.TreeScope]
$CT = [System.Windows.Automation.ControlType]
$STILLS = @(('HeroVerse ' + [char]0x2014 + ' stills'), ('HeroVerse ' + [char]0x2013 + ' stills'), 'HeroVerse - stills')
$MARKERS = @('Create an image, 16:9 landscape, no text.', 'Create an image, 9:16 vertical portrait, no text.')
$ui = 'C:\HeroVerse\ui.ps1'

function Out-Result($word, $detail, [int]$code) { if ($detail) { "$word $detail" } else { $word }; exit $code }
function Test-Stills($name) { return ($name -and ($STILLS -ccontains $name.Trim())) }
function Get-Key($e) { try { return ($e.GetRuntimeId() -join '.') } catch { return '' } }

function Test-OwnerActive {
  if ($idle -le 0) { return $false }
  $since = [HVGuard]::IdleSeconds()
  if ($since -ge $idle) { return $false }
  $mine = 1e9
  if (Test-Path 'C:\HeroVerse\lastact.txt') {
    try { $mine = [HVGuard]::SinceTick([int64](Get-Content 'C:\HeroVerse\lastact.txt' -ErrorAction Stop | Select-Object -First 1)) } catch { $mine = 1e9 }
  }
  # the last input is ours only when it is not newer than this route's last action (1.5 s slack)
  return ($since -lt ($mine - 1.5))
}

function Get-Root {
  $p = Get-Process -Name ChatGPT -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
  if (-not $p) { return $null }
  return $A::FromHandle($p.MainWindowHandle)
}

function Get-State($root) {
  $s = @{ doc = $false; sidebar = 0; selected = $false; header = $false; markers = 0; button = $null; edits = @() }
  $all = $root.FindAll($TS::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
  $inEdit = @{}
  foreach ($e in $all) {
    try { if ($e.Current.ControlType -eq $CT::Edit) {
      $s.edits += $e; $inEdit[(Get-Key $e)] = 1
      foreach ($d in $e.FindAll($TS::Descendants, [System.Windows.Automation.Condition]::TrueCondition)) { $inEdit[(Get-Key $d)] = 1 }
    } } catch {}
  }
  foreach ($e in $all) {
    try { $c = $e.Current } catch { continue }
    $n = $c.Name
    if (-not $n) { continue }
    if (Test-Stills $n) {
      $tokens = @("$($c.ClassName)" -split '\s+')
      if ($c.ControlType -eq $CT::Document) { $s.doc = $true }
      elseif ($c.ControlType -eq $CT::Button -and ($tokens -ccontains 'sidebar-item')) {
        $s.sidebar++; $s.button = $e
        if ($tokens -ccontains 'bg-primary-ghost-hover') { $s.selected = $true }
      }
      elseif ($c.ControlType -eq $CT::Button -and ($tokens -ccontains 'px-button-toolbar-inline')) { $s.header = $true }
    }
    if ($c.ControlType -ne $CT::Edit -and -not $inEdit.ContainsKey((Get-Key $e))) {
      foreach ($m in $MARKERS) { if ($n.Contains($m)) { $s.markers++; break } }
    }
  }
  return $s
}

function Test-Verified($s) { return ($s.doc -and ($s.selected -or $s.header) -and $s.markers -ge 1 -and $s.sidebar -le 1) }
function Format-State($s) { "doc=$($s.doc) sidebarItems=$($s.sidebar) sidebarSelected=$($s.selected) header=$($s.header) markers=$($s.markers)" }

function Invoke-Element($e) {
  try { $e.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); return $true } catch {}
  try { $e.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select(); return $true } catch {}
  return $false
}

function Test-PaletteRow($name) {
  # a search-palette row is named "<chat title> ChatGPT Alt+<n>" (measured 2026-11-05): the title must be exactly the
  # stills name and only the app's own label may follow, so "HeroVerse - stills 2" or a longer title never matches
  if (-not $name -or $name.Length -lt 18) { return $false }
  return (($STILLS -ccontains $name.Substring(0, 18)) -and ($name.Substring(18) -cmatch '^ ChatGPT( Alt\+\d)?$'))
}

function Select-ViaSearch($root) {
  # The app's own search palette (Ctrl+K, measured 2026-11-05: a NEW focused ComboBox over invokable chat rows).
  # 'stills' is typed only into that new focused box, and only ONE row named exactly for the stills chat that appeared
  # with the palette is opened with a UIA Invoke. Enter is never pressed; any doubt closes the palette (Esc).
  $before = @{}
  foreach ($e in $root.FindAll($TS::Descendants, [System.Windows.Automation.Condition]::TrueCondition)) { $before[(Get-Key $e)] = 1 }
  $r = & $ui -act type -text '^k' -wait 1 -out 'C:\HeroVerse\guard.png'
  if ("$r" -notmatch 'ok') { return 'focus' }
  $box = $null
  for ($i = 0; $i -lt 10 -and -not $box; $i++) {
    try { $f = $A::FocusedElement
          if ($f.Current.ControlType -eq $CT::ComboBox -and -not $before.ContainsKey((Get-Key $f))) { $box = $f } } catch {}
    if (-not $box) { Start-Sleep -m 300 }
  }
  if (-not $box) { & $ui -act type -text '{ESC}' -wait 1 | Out-Null; return 'no_search_box' }
  $r = & $ui -act type -text 'stills' -wait 3 -out 'C:\HeroVerse\guard.png'
  $v = ''; try { $v = $box.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).Current.Value } catch {}
  if ("$r" -notmatch 'ok' -or $v -cne 'stills') { & $ui -act type -text '{ESC}' -wait 1 | Out-Null; return 'search_box_value' }
  $rows = @()
  foreach ($e in $root.FindAll($TS::Descendants, (New-Object System.Windows.Automation.PropertyCondition($A::ControlTypeProperty, $CT::ListItem)))) {
    try { if (-not $before.ContainsKey((Get-Key $e)) -and (Test-PaletteRow $e.Current.Name)) { $rows += $e } } catch {}
  }
  if (@($rows).Count -ne 1) { & $ui -act type -text '{ESC}' -wait 1 | Out-Null; return "search_rows=$(@($rows).Count)" }
  try { @($rows)[0].GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }
  catch { & $ui -act type -text '{ESC}' -wait 1 | Out-Null; return 'invoke_failed' }
  return ''
}

if (Test-OwnerActive) { Out-Result 'OWNER_ACTIVE' "idle_s=$([math]::Round([HVGuard]::IdleSeconds()))" 3 }
$root = Get-Root
if (-not $root) { Out-Result 'WRONG_CHAT' 'no_window' 4 }
$s = Get-State $root
if ($s.sidebar -gt 1) { Out-Result 'WRONG_CHAT' "ambiguous sidebarItems=$($s.sidebar)" 4 }
if (-not $verifyOnly -and -not (Test-Verified $s)) {
  $how = ''
  if ($s.button -and -not $viaSearch) { $how = 'sidebar'; if (-not (Invoke-Element $s.button)) { Out-Result 'WRONG_CHAT' 'sidebar_invoke_failed' 4 } }
  else {
    if (Test-OwnerActive) { Out-Result 'OWNER_ACTIVE' '' 3 }
    $how = 'search'; $why = Select-ViaSearch $root
    if ($why) { Out-Result 'WRONG_CHAT' "not_found $why" 4 }
  }
  for ($i = 0; $i -lt 8; $i++) { Start-Sleep 2; $s = Get-State $root; if (Test-Verified $s) { break } }
  "SELECTED via=$how"
}
if (Test-OwnerActive) { Out-Result 'OWNER_ACTIVE' '' 3 }
"SIGNALS " + (Format-State $s)
if (-not (Test-Verified $s)) { Out-Result 'WRONG_CHAT' '' 4 }
Out-Result 'OK' '' 0
