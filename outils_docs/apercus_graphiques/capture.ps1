# Capture des 4 pages en PNG par Chrome sans tete (900x450)
$d = $PSScriptRoot
$chrome = 'C:\Program Files\Google\Chrome\Application\chrome.exe'
foreach ($n in 'uplot','chartjs','echarts','apexcharts') {
  $url = 'file:///' + ($d -replace '\\','/') + "/$n.html"
  $args2 = @('--headless=new','--disable-gpu','--hide-scrollbars','--window-size=900,450','--virtual-time-budget=8000',"--screenshot=$d\$n.png",$url)
  Start-Process -Wait -FilePath $chrome -ArgumentList $args2
}
