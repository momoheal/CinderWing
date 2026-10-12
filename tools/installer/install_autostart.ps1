# 开机自启-安装：在当前用户的"启动"文件夹里放一个指向桌宠 exe 的快捷方式。
# 不需要管理员权限，只影响当前用户。
$ErrorActionPreference = "Stop"
$exe = Join-Path $PSScriptRoot "小死亡之翼桌宠.exe"
if (-not (Test-Path $exe)) {
    [System.Windows.Forms.MessageBox]::Show("没找到 $exe，请把本脚本和 exe 放在同一个文件夹。")
    exit 1
}
$startup = [Environment]::GetFolderPath("Startup")
$lnk = Join-Path $startup "小死亡之翼桌宠.lnk"
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut($lnk)
$s.TargetPath = $exe
$s.WorkingDirectory = $PSScriptRoot
$s.WindowStyle = 7          # 最小化（桌宠本身也没有控制台窗口）
$s.Description = "小死亡之翼桌宠（开机自动启动）"
$s.IconLocation = "$exe,0"
$s.Save()
Write-Host "已安装开机自启：$lnk"
