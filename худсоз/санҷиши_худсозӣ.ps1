# санҷиши_худсозӣ.ps1 — санҷиши нуқтаи собит (fixed point).
#
# Насли 0: тарҷумони асосӣ файлҳои .tj-ро ба .js табдил медиҳад.
# Насли 1: ҳамон .js файлҳо худи ҳамон .tj файлҳоро дубора тарҷума мекунанд.
# Насли 2: боз як бор.
#
# Агар насли 1 ва насли 2 ҳарф ба ҳарф баробар бошанд, тарҷумон нуқтаи собит
# дорад — яъне забон воқеан худашро месозад.

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$файлҳо = @('лексер.js', 'тарҷумон.js', 'худсозӣ.js')

foreach ($н in 0..2) {
    $ҷузвдон = "насли$н"
    Remove-Item -Recurse -Force $ҷузвдон -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path $ҷузвдон | Out-Null
}

Write-Host '--- насли 0: тарҷумони асосӣ ---'
& tajik худсозӣ.tj
if ($LASTEXITCODE -ne 0) { throw 'насли 0 иҷро нашуд' }
Copy-Item $файлҳо насли0\ -Force

Write-Host ''
Write-Host '--- насли 1: JavaScript худашро месозад ---'
& node худсозӣ.js
if ($LASTEXITCODE -ne 0) { throw 'насли 1 иҷро нашуд' }
Copy-Item $файлҳо насли1\ -Force

Write-Host ''
Write-Host '--- насли 2: боз як бор ---'
& node худсозӣ.js
if ($LASTEXITCODE -ne 0) { throw 'насли 2 иҷро нашуд' }
Copy-Item $файлҳо насли2\ -Force

Write-Host ''
$хато = $false
$реша = $PSScriptRoot

function Санҷидан($чап, $рост, $ном, $тавсиф) {
    $a = [System.IO.File]::ReadAllText((Join-Path $реша "$чап\$ном"))
    $b = [System.IO.File]::ReadAllText((Join-Path $реша "$рост\$ном"))
    if ($a -ceq $b) {
        Write-Host "  баробар   $тавсиф  $ном  ($($a.Length) ҳарф)"
        return $true
    }
    Write-Host "  ФАРҚ ДОРАД  $тавсиф  $ном  ($($a.Length) ва $($b.Length) ҳарф)"
    return $false
}

foreach ($ф in $файлҳо) {
    # Насли 1 == насли 2: тарҷумон нуқтаи собит дорад.
    if (-not (Санҷидан 'насли1' 'насли2' $ф 'насл 1↔2')) { $хато = $true }
    # Насли 0 == насли 1: ду муҳити тамоман гуногун ҳамон натиҷа медиҳанд.
    if (-not (Санҷидан 'насли0' 'насли1' $ф 'насл 0↔1')) { $хато = $true }
}

Write-Host ''
if ($хато) {
    Write-Host 'Нуқтаи собит ёфт нашуд.'
    exit 1
}
Write-Host 'НУҚТАИ СОБИТ: тарҷумон худашро айнан такрор мекунад.'
