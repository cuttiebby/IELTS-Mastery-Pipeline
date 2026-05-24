$url = "https://fonts.gstatic.com/s/notosanssc/v40/k3kCo84MPvpLmixcA63oeAL7Iqp5IZJF9bmaG9_FnYw.ttf"
$dest = "d:\TrialCode\fonts\NotoSansSC-Regular.ttf"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Invoke-WebRequest -Uri $url -OutFile $dest -UserAgent "Mozilla/5.0"
Write-Host "Downloaded: $dest"
Get-Item $dest | Select-Object Name, Length, LastWriteTime