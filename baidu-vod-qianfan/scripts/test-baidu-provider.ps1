[CmdletBinding()]
param(
    [ValidateSet('All', 'Vod', 'NewVod', 'Qianfan')]
    [string]$Provider = 'All',

    [string[]]$VodModels = @(
        'deepseek-v4-flash',
        'deepseek-v4-pro',
        'glm-5.2',
        'glm-5.3',
        'glm-5.3-flash',
        'kimi-k3'
    ),

    [string[]]$NewVodModels = @(
        'deepseek-v4-flash',
        'deepseek-v4-pro',
        'glm-5.2',
        'glm-5.3',
        'glm-5.3-flash',
        'kimi-k3'
    ),

    [string[]]$QianfanModels = @(
        'deepseek-v4-flash-0731',
        'deepseek-v4-pro',
        'deepseek-v4.1-flash',
        'glm-5.2',
        'glm-5.3'
    ),

    [ValidateRange(1, 300)]
    [int]$TimeoutSeconds = 60
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

function Get-RequiredEnvironmentValue {
    param([Parameter(Mandatory)][string]$Name)

    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Required environment variable $Name is not set."
    }
    return $value.Trim()
}

function Join-ProviderEndpoint {
    param(
        [Parameter(Mandatory)][string]$BaseUrl,
        [Parameter(Mandatory)][string]$Path
    )

    $normalizedBase = $BaseUrl.TrimEnd('/')
    if ($normalizedBase.EndsWith($Path, [StringComparison]::OrdinalIgnoreCase)) {
        return $normalizedBase
    }
    return $normalizedBase + $Path
}

function Protect-Secrets {
    param([AllowEmptyString()][string]$Text)

    if ($null -eq $Text) {
        return ''
    }
    foreach ($secret in @($script:VodKey, $script:NewVodKey, $script:QianfanKey)) {
        if (-not [string]::IsNullOrEmpty($secret)) {
            $Text = $Text.Replace($secret, '[REDACTED]')
        }
    }
    return $Text
}

function Get-ResponseText {
    param([AllowEmptyString()][string]$Body)

    if ([string]::IsNullOrWhiteSpace($Body)) {
        return '(empty response body)'
    }
    try {
        $parsed = $Body | ConvertFrom-Json
        if ($null -ne $parsed.choices -and $parsed.choices.Count -gt 0) {
            $content = $parsed.choices[0].message.content
            if (-not [string]::IsNullOrWhiteSpace([string]$content)) {
                return [string]$content
            }
            $reasoning = $parsed.choices[0].message.reasoning_content
            if (-not [string]::IsNullOrWhiteSpace([string]$reasoning)) {
                return "reasoning: $reasoning"
            }
        }
        if ($null -ne $parsed.error) {
            if (-not [string]::IsNullOrWhiteSpace([string]$parsed.error.message)) {
                return [string]$parsed.error.message
            }
            return ($parsed.error | ConvertTo-Json -Compress -Depth 20)
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$parsed.message)) {
            return [string]$parsed.message
        }
    }
    catch {
        # Preserve the raw upstream body when it is not valid JSON.
    }
    return $Body
}

function Invoke-ProviderModel {
    param(
        [Parameter(Mandatory)][string]$ProviderName,
        [Parameter(Mandatory)][string]$Endpoint,
        [Parameter(Mandatory)][string]$ApiKey,
        [Parameter(Mandatory)][string]$Model
    )

    $payload = @{
        model = $Model
        messages = @(
            @{ role = 'user'; content = '你好' }
        )
        max_tokens = 64
        stream = $false
    } | ConvertTo-Json -Compress -Depth 10

    $handler = [System.Net.Http.HttpClientHandler]::new()
    $client = [System.Net.Http.HttpClient]::new($handler)
    $client.Timeout = [TimeSpan]::FromSeconds($TimeoutSeconds)
    $request = [System.Net.Http.HttpRequestMessage]::new([System.Net.Http.HttpMethod]::Post, $Endpoint)
    $request.Headers.Authorization = [System.Net.Http.Headers.AuthenticationHeaderValue]::new('Bearer', $ApiKey)
    $request.Headers.Accept.ParseAdd('application/json')
    $request.Content = [System.Net.Http.StringContent]::new($payload, [System.Text.Encoding]::UTF8, 'application/json')
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

    try {
        $response = $client.SendAsync($request).GetAwaiter().GetResult()
        $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        $stopwatch.Stop()
        $statusCode = [int]$response.StatusCode
        $statusName = [string]$response.StatusCode
        $result = Protect-Secrets (Get-ResponseText $body)
        [Console]::Out.WriteLine("[$ProviderName] $Model - HTTP $statusCode $statusName - $($stopwatch.ElapsedMilliseconds) ms")
        if ($response.IsSuccessStatusCode) {
            [Console]::Out.WriteLine("reply: $result")
            return $true
        }
        [Console]::Out.WriteLine("error: $result")
        return $false
    }
    catch {
        $stopwatch.Stop()
        $message = Protect-Secrets $_.Exception.GetBaseException().Message
        [Console]::Out.WriteLine("[$ProviderName] $Model - TRANSPORT_ERROR - $($stopwatch.ElapsedMilliseconds) ms")
        [Console]::Out.WriteLine("error: $message")
        return $false
    }
    finally {
        $request.Dispose()
        $client.Dispose()
        $handler.Dispose()
    }
}

$script:VodKey = $null
$script:NewVodKey = $null
$script:QianfanKey = $null
$vodEndpoint = $null
$newVodEndpoint = $null
$qianfanEndpoint = $null

try {
    if ($Provider -in @('All', 'Vod')) {
        $vodBaseUrl = Get-RequiredEnvironmentValue 'BAIDU_VOD_URL'
        $script:VodKey = Get-RequiredEnvironmentValue 'BAIDU_VOD_KEY'
        $vodEndpoint = Join-ProviderEndpoint $vodBaseUrl '/v1/chat/completions'
    }
    if ($Provider -in @('All', 'NewVod')) {
        $newVodBaseUrl = Get-RequiredEnvironmentValue 'BAIDU_NEWVOD_URL'
        $script:NewVodKey = Get-RequiredEnvironmentValue 'BAIDU_NEWVOD_KEY'
        $newVodEndpoint = Join-ProviderEndpoint $newVodBaseUrl '/v1/chat/completions'
    }
    if ($Provider -in @('All', 'Qianfan')) {
        $qianfanBaseUrl = Get-RequiredEnvironmentValue 'BAIDU_QF_URL'
        $script:QianfanKey = Get-RequiredEnvironmentValue 'BAIDU_QF_KEY'
        $qianfanEndpoint = Join-ProviderEndpoint $qianfanBaseUrl '/v2/chat/completions'
    }
}
catch {
    [Console]::Error.WriteLine((Protect-Secrets $_.Exception.Message))
    exit 2
}

$hadFailure = $false
if ($Provider -in @('All', 'Vod')) {
    foreach ($model in $VodModels) {
        if (-not (Invoke-ProviderModel 'VOD' $vodEndpoint $script:VodKey $model)) {
            $hadFailure = $true
        }
    }
}
if ($Provider -in @('All', 'NewVod')) {
    foreach ($model in $NewVodModels) {
        if (-not (Invoke-ProviderModel 'NEW_VOD' $newVodEndpoint $script:NewVodKey $model)) {
            $hadFailure = $true
        }
    }
}
if ($Provider -in @('All', 'Qianfan')) {
    foreach ($model in $QianfanModels) {
        if (-not (Invoke-ProviderModel 'QF' $qianfanEndpoint $script:QianfanKey $model)) {
            $hadFailure = $true
        }
    }
}

if ($hadFailure) {
    exit 1
}
exit 0
