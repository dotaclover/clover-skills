$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
[Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.FileAccessMode, Windows.Storage, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.SoftwareBitmap, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Media.Ocr.OcrResult, Windows.Foundation, ContentType=WindowsRuntime] | Out-Null
[Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime] | Out-Null
function Await($Operation, $ResultType) {
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.Wait()
    return $task.Result
}
$root = 'C:/code/cloverhub/clover-skills/xunzhao-chuangye-xiangmu'
$lang = [Windows.Globalization.Language]::new('zh-Hans-CN')
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
$records = @()
$folders = @('images', 'exams', 'example', 'examples')
foreach ($folder in $folders) {
    $dir = Join-Path (Join-Path $root '_ocr_prepared') $folder
    if (-not (Test-Path -LiteralPath $dir)) { continue }
    $files = Get-ChildItem -LiteralPath $dir -File | Where-Object { $_.Extension -match '^\.(jpg|jpeg|png)$' -and $_.Name -notmatch '^contact-' } | Sort-Object Name
    foreach ($file in $files) {
        $bitmap = $null
        $stream = $null
        try {
            $storageFile = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($file.FullName)) ([Windows.Storage.StorageFile])
            $stream = Await ($storageFile.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
            $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
            $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
            if ($bitmap.PixelWidth -gt [Windows.Media.Ocr.OcrEngine]::MaxImageDimension -or $bitmap.PixelHeight -gt [Windows.Media.Ocr.OcrEngine]::MaxImageDimension) {
                throw 'Image exceeds native OCR engine maximum size.'
            }
            $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
            $lines = @($result.Lines | ForEach-Object { $_.Text })
            $records += [PSCustomObject]@{ source = "$folder/$($file.Name)"; status = 'ocr_extracted_not_visually_verified'; width = $bitmap.PixelWidth; height = $bitmap.PixelHeight; lines = $lines; error = '' }
            Write-Output ("OK {0} {1} lines" -f $file.Name, $lines.Count)
        } catch {
            $records += [PSCustomObject]@{ source = "$folder/$($file.Name)"; status = 'error'; lines = @(); error = $_.Exception.Message }
            Write-Output ("ERROR {0}: {1}" -f $file.Name, $_.Exception.Message)
        } finally {
            if ($bitmap) { $bitmap.Dispose() }
            if ($stream) { $stream.Dispose() }
        }
    }
}
$out = Join-Path $root 'course-ocr.json'
[System.IO.File]::WriteAllText($out, (ConvertTo-Json -InputObject @($records) -Depth 8), [System.Text.UTF8Encoding]::new($false))
Write-Output ("DONE {0} records" -f $records.Count)
