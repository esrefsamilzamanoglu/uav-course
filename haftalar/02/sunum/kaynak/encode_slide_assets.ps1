# Encode unchanged generated PNGs as JPEG for compact PowerPoint embedding.
# Source PNGs are retained; no drawing, crop, resize or content editing occurs.
param([int]$Quality = 92)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$assetRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../uretilen_gorseller'))
$jpegCodec = [Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object MimeType -eq 'image/jpeg'
foreach ($assetFile in Get-ChildItem -LiteralPath $assetRoot -Filter 'slide-*.png') {
    $picture = [Drawing.Image]::FromFile($assetFile.FullName)
    $parameters = New-Object Drawing.Imaging.EncoderParameters 1
    try {
        $parameters.Param[0] = New-Object Drawing.Imaging.EncoderParameter ([Drawing.Imaging.Encoder]::Quality), ([long]$Quality)
        $destination = [IO.Path]::ChangeExtension($assetFile.FullName, '.jpg')
        $picture.Save($destination, $jpegCodec, $parameters)
    }
    finally { $picture.Dispose(); $parameters.Dispose() }
}
Write-Output 'JPEG slide copies encoded at original dimensions; source PNGs preserved.'
