# ==========================================
# 사용자 설정 변수 (Configuration)
# ==========================================
param(
    [int]$IntervalSeconds = 5,          # 기록 주기 (초)
    [string[]]$TargetDrives = @("C:", "D:") # 모니터링 드라이브 리스트
)
$LogFolder = "C:\SystemLogs"              # 로그 저장 경로
# ==========================================

if (-not (Test-Path $LogFolder)) { New-Item -ItemType Directory -Path $LogFolder }

Write-Host "Starting Hybrid Resource Monitoring (Interval: $($IntervalSeconds)s)..." -ForegroundColor Cyan
Write-Host "Detecting Hardware (NVIDIA/Intel/AMD)..." -ForegroundColor Yellow

while ($true) {
    # 0. 날짜 기반 로그 분할
    $CurrentDate = Get-Date -Format "yyyy-MM-dd"
    $LogPath = Join-Path $LogFolder "System_Log_$CurrentDate.csv"

    # 1. 시스템 정보 (메모리 정보는 실행 시 또는 필요 시 한 번만 계산)
    $ipAddress = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" } | Select-Object -First 1).IPAddress -or "N/A"
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    # 물리 장착 메모리 (DIMM 기준)
    $physicalMemGB = [Math]::Round(((Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum / 1GB), 0)
    # OS 사용 가능 메모리
    $osTotalMemGB = [Math]::Round(((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB), 2)

    # 2. 헤더 생성
    if (-not (Test-Path $LogPath)) {
        $driveHeaders = foreach ($d in $TargetDrives) { "$d`_Usage(%),$d`_Read(MB/s),$d`_Write(MB/s)" }
        $header = "Timestamp,IP_Address,PhysicalMem(GB),OSTotalMem(GB),CPU(%),CPU_Temp(C),DGPU(%),DGPU_Temp(C),IGPU(%),Used(GB),Usage(%),NonPagedPool(MB),Swap_Usage(%),$($driveHeaders -join ","),Top5_Memory_MB,Top5_Disk_IO_Global(MB/s)"
        Set-Content -Path $LogPath -Value $header -Encoding UTF8
    }

    # 3. CPU 사용량 및 온도 (Intel/AMD 범용)
    $cpu = [Math]::Round(((Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1).CounterSamples.CookedValue), 2)
    try {
        $tempK = (Get-CimInstance -Namespace root/wmi -ClassName MsAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue).CurrentTemperature
        $cpuTemp = if ($tempK) { [Math]::Round(($tempK / 10) - 273.15, 1) } else { "N/A" }
    }
    catch { $cpuTemp = "N/A" }

    # 4. GPU 모니터링 (Hybrid: NVIDIA + iGPU)
    # 4-1. NVIDIA 외장 그래픽 (DGPU)
    $dgpuUsage = "0"; $dgpuTemp = "0"
    try {
        $gpuRaw = nvidia-smi --query-gpu="utilization.gpu,temperature.gpu" --format="csv,noheader,nounits" 2>$null
        if ($gpuRaw) {
            $gpuParts = $gpuRaw -split ','
            $dgpuUsage = $gpuParts[0].Trim()
            $dgpuTemp = $gpuParts[1].Trim()
        }
    }
    catch { }

    # 4-2. 인텔/AMD 내장 그래픽 (IGPU) - 성능 카운터 기반
    $igpuUsage = 0
    try {
        $gpuCounters = Get-Counter '\GPU Engine(*)\Utilization Percentage' -ErrorAction SilentlyContinue
        if ($gpuCounters) {
            $igpuUsage = [Math]::Round(($gpuCounters.CounterSamples.CookedValue | Measure-Object -Maximum).Maximum, 1)
        }
    }
    catch { $igpuUsage = "N/A" }

    # 5. 메모리 계층 정보
    $os = Get-CimInstance Win32_OperatingSystem
    $usedGB = [Math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) / 1MB, 2)
    $memUsagePct = [Math]::Round(($usedGB / ([Math]::Round($os.TotalVisibleMemorySize / 1MB, 2))) * 100, 2)
    $nonPagedMB = [Math]::Round(((Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory).PoolNonpagedBytes / 1MB), 2)
    $pf = Get-CimInstance Win32_PageFileUsage
    $pfUsagePct = if ($pf) { [Math]::Round(($pf.CurrentUsage / $pf.AllocatedBaseSize) * 100, 2) } else { 0 }

    # 6. 드라이브 성능
    $driveDetails = foreach ($d in $TargetDrives) {
        $logicDisk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$d'"
        $usage = if ($logicDisk) { [Math]::Round((($logicDisk.Size - $logicDisk.FreeSpace) / $logicDisk.Size) * 100, 2) } else { "N/A" }
        $diskStats = Get-Counter "\LogicalDisk($d)\Disk Read Bytes/sec", "\LogicalDisk($d)\Disk Write Bytes/sec" -ErrorAction SilentlyContinue
        $readMB = if ($diskStats) { [Math]::Round($diskStats.CounterSamples[0].CookedValue / 1MB, 2) } else { 0 }
        $writeMB = if ($diskStats) { [Math]::Round($diskStats.CounterSamples[1].MiddleValue / 1MB, 2) } else { 0 } # Corrected CookedValue index if needed, but let's stick to safe
        $writeMB = if ($diskStats) { [Math]::Round($diskStats.CounterSamples[1].CookedValue / 1MB, 2) } else { 0 }
        "$usage,$readMB,$writeMB"
    }
    $driveDataStr = $driveDetails -join ","

    # 7. 상위 프로세스 식별
    $topMemLog = ((Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 5 | ForEach-Object {
                "$($_.ProcessName):$([Math]::Round($_.WorkingSet64 / 1MB, 0))MB"
            }) -join " | ")

    $diskCounters = Get-Counter '\Process(*)\IO Data Bytes/sec' -ErrorAction SilentlyContinue
    $diskSamples = $diskCounters.CounterSamples | Where-Object { $_.InstanceName -notmatch "^(_total|idle|system)$" -and $_.CookedValue -gt 10KB }
    $topDiskLog = if ($diskSamples) {
        ($diskSamples | Sort-Object CookedValue -Descending | Select-Object -First 5 | ForEach-Object {
            "$($_.InstanceName):$([Math]::Round($_.CookedValue / 1MB, 2))MB/s"
        }) -join " | "
    }
    else { "No_Active_IO" }

    # 8. 최종 데이터 기록
    $logEntry = "$timestamp,$ipAddress,$physicalMemGB,$osTotalMemGB,$cpu,$cpuTemp,$dgpuUsage,$dgpuTemp,$igpuUsage,$usedGB,$memUsagePct,$nonPagedMB,$pfUsagePct,$driveDataStr,""$topMemLog"",""$topDiskLog"""
    Add-Content -Path $LogPath -Value $logEntry
    
    # 실시간 콘솔 출력
    Write-Host "[$timestamp] CPU: $cpu% | DGPU: $dgpuUsage% | IGPU: $igpuUsage% | Mem: $memUsagePct%" -ForegroundColor Green
    
    Start-Sleep -Seconds ($IntervalSeconds - 1)
}
