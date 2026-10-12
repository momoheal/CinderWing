# 开机自启-卸载：删除"启动"文件夹里的桌宠快捷方式（不会删除程序本身）。
$startup = [Environment]::GetFolderPath("Startup")
$lnk = Join-Path $startup "CinderWing.lnk"
if (Test-Path $lnk) {
    Remove-Item $lnk -Force
    Write-Host "已移除开机自启：$lnk"
} else {
    Write-Host "没有找到开机自启项，无需移除。"
}
