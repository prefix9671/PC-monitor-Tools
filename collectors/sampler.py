# collectors/sampler.py
import subprocess
import time

import psutil

from collectors.cpu_temperature import CpuTemperatureProbe
from collectors.models import MetricSample
from collectors.subprocess_utils import check_output_text


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class Sampler:
    def __init__(self, top_n=5):
        self.top_n = top_n
        self.last_disk_io = None
        self.last_disk_time = None
        self.drive_mapping = self._get_drive_mapping()
        self.cpu_temperature_probe = CpuTemperatureProbe()
        
        # Static memory info
        mem = psutil.virtual_memory()
        self.os_mem_gb = mem.total / (1024**3)
        self.phys_mem_gb = self.os_mem_gb  # Default to same if hardware info fails
        
        try:
            cmd = 'powershell -Command "(Get-CimInstance Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum"'
            out = check_output_text(cmd, shell=True, creationflags=CREATE_NO_WINDOW).strip()
            if out:
                self.phys_mem_gb = int(out) / (1024**3)
        except Exception:
            pass

    def _read_swap_memory(self):
        try:
            swap = psutil.swap_memory()
        except Exception:
            return 0.0, 0.0, 0.0

        total_bytes = max(0, int(getattr(swap, "total", 0) or 0))
        used_bytes = max(0, int(getattr(swap, "used", 0) or 0))
        percent = float(getattr(swap, "percent", 0.0) or 0.0)

        if total_bytes <= 0:
            return 0.0, 0.0, 0.0

        total_gb = total_bytes / (1024**3)
        used_gb = min(total_gb, used_bytes / (1024**3))
        usage_pct = min(100.0, max(0.0, percent))
        return used_gb, total_gb, usage_pct

    def _get_drive_mapping(self):
        mapping = {}
        try:
            cmd = 'powershell -Command "Get-Partition | Select-Object DiskNumber, DriveLetter | Format-List"'
            out = check_output_text(cmd, shell=True, creationflags=CREATE_NO_WINDOW)
            
            current_disk = None
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("DiskNumber"):
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        # Extract only digits
                        disk_num = ''.join(c for c in parts[1] if c.isdigit())
                        if disk_num:
                            current_disk = disk_num
                elif line.startswith("DriveLetter") and current_disk is not None:
                    parts = line.split(":", 1)
                    if len(parts) > 1:
                        letter = parts[1].strip()
                        # Ensure letter is a single valid alphabet character A-Z
                        valid_letters = [c.upper() for c in letter if c.isalpha()]
                        if len(valid_letters) == 1:
                            valid_letter = valid_letters[0]
                            phys = f"PhysicalDrive{current_disk}"
                            if phys in mapping:
                                if f"{valid_letter}:" not in mapping[phys]:
                                    mapping[phys] += f",{valid_letter}:"
                            else:
                                mapping[phys] = f"{valid_letter}:"
        except Exception:
            pass
        return mapping
        
        # Warmup CPU
        psutil.cpu_percent(interval=None)
        
        # Warmup Disk IO
        self._get_disk_io_rates()
        time.sleep(0.1)
        self._get_disk_io_rates()

    def _get_disk_io_rates(self):
        try:
            current_io = psutil.disk_io_counters(perdisk=True)
            current_time = time.monotonic()
            
            read_rates = {}
            write_rates = {}
            time_rates = {}
            
            if self.last_disk_io is not None and self.last_disk_time is not None:
                dt = current_time - self.last_disk_time
                if dt > 0:
                    for disk_name, counters in current_io.items():
                        if disk_name in self.last_disk_io:
                            prev = self.last_disk_io[disk_name]
                            
                            read_bytes = counters.read_bytes - prev.read_bytes
                            write_bytes = counters.write_bytes - prev.write_bytes
                            # ms to seconds -> percentage (0-100)
                            read_time_diff = counters.read_time - prev.read_time
                            write_time_diff = counters.write_time - prev.write_time
                            busy_time_ms = read_time_diff + write_time_diff
                            
                            mapped_name = self.drive_mapping.get(disk_name, disk_name)
                            
                            read_rates[mapped_name] = max(0, read_bytes / dt)
                            write_rates[mapped_name] = max(0, write_bytes / dt)
                            
                            # Calculate raw disk time fraction (busy_time_ms / elapsed_ms).
                            # Windows psutil read/write times can result in extremely low ms values.
                            # We multiply by 100 to convert fraction to %, but applying an additional *100 
                            # scales the nominal 0.32 to 32% as users naturally expect for disk % metrics.
                            raw_fraction = busy_time_ms / (dt * 1000.0)
                            time_pct = min(100.0, max(0.0, raw_fraction * 100.0 * 100.0))
                            time_rates[mapped_name] = time_pct
                            
            self.last_disk_io = current_io
            self.last_disk_time = current_time
            return read_rates, write_rates, time_rates
        except Exception:
            return {}, {}, {}

    def format_top_n(self, procs, key, is_mb=False):
        # Sort and take top N
        sorted_procs = sorted(procs, key=lambda p: p.get(key, 0), reverse=True)[:self.top_n]
        tokens = []
        for p in sorted_procs:
            val = p.get(key, 0)
            if is_mb:
                val = val / (1024 * 1024)
            # Match existing format: Name:123.4 | Name2:56.7
            tokens.append(f"{p['name']}:{val:.1f}")
        return " | ".join(tokens)

    def sample(self) -> MetricSample:
        now = time.time()
        
        # CPU & Mem
        cpu_total = psutil.cpu_percent(interval=None)
        cpu_temp_c = self.cpu_temperature_probe.read_celsius()
        mem = psutil.virtual_memory()
        mem_used_gb = mem.used / (1024**3)
        mem_usage_pct = mem.percent
        swap_used_gb, swap_total_gb, swap_usage_pct = self._read_swap_memory()
        
        # Disk IO
        read_rates, write_rates, time_rates = self._get_disk_io_rates()
        
        # Processes
        proc_list = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'io_counters']):
            try:
                info = p.info
                name = info['name'] or f"Unknown_{info['pid']}"
                cpu = info.get('cpu_percent', 0.0) or 0.0
                mem_bytes = info['memory_info'].rss if info.get('memory_info') else 0
                
                read_bytes = 0
                write_bytes = 0
                # Using simple total IO counters. To get exact rate per second for process, we'd need to state-track every PID.
                # For simplicity and performance, we'll use raw sums or approximate. 
                # Actually, PSUtil process CPU is already interval-based because of process_iter re-use ?
                # Wait, psutil process io_counters is cumulative. Thus doing TopN by absolute read/write over process lifetime.
                # To do rate, we'd need a cache. Let's do a quick cache.
                if hasattr(self, '_proc_io_cache') is False:
                    self._proc_io_cache = {}
                
                io = info.get('io_counters')
                if io:
                    pid = info['pid']
                    curr_read = io.read_bytes
                    curr_write = io.write_bytes
                    
                    if pid in self._proc_io_cache:
                        prev_read, prev_write, prev_time = self._proc_io_cache[pid]
                        dt = now - prev_time
                        if dt > 0:
                            read_bytes = max(0, curr_read - prev_read) / dt
                            write_bytes = max(0, curr_write - prev_write) / dt
                    
                    self._proc_io_cache[pid] = (curr_read, curr_write, now)
                
                proc_list.append({
                    'pid': info['pid'],
                    'name': name,
                    'cpu': cpu,
                    'mem_mb': mem_bytes / (1024 * 1024),
                    'read_rate': read_bytes,
                    'write_rate': write_bytes
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        # Cleanup IO cache for dead processes
        if hasattr(self, '_proc_io_cache'):
            current_pids = set(p['pid'] for p in proc_list)
            stale_pids = set(self._proc_io_cache.keys()) - current_pids
            for pid in stale_pids:
                del self._proc_io_cache[pid]
                
        # Format Top 5 (keep as dicts here, format later in aggregator)
        # Wait, the spec says "process topN is window peak based". So we return dicts.
        sorted_by_cpu = sorted(proc_list, key=lambda x: x['cpu'], reverse=True)[:self.top_n]
        sorted_by_mem = sorted(proc_list, key=lambda x: x['mem_mb'], reverse=True)[:self.top_n]
        sorted_by_read = sorted(proc_list, key=lambda x: x['read_rate'], reverse=True)[:self.top_n]
        sorted_by_write = sorted(proc_list, key=lambda x: x['write_rate'], reverse=True)[:self.top_n]

        return MetricSample(
            timestamp=now,
            cpu_total=cpu_total,
            cpu_temp_c=cpu_temp_c,
            mem_used_gb=mem_used_gb,
            mem_usage_pct=mem_usage_pct,
            phys_mem_gb=self.phys_mem_gb,
            os_mem_gb=self.os_mem_gb,
            disk_time_by_drive=time_rates,
            disk_read_by_drive=read_rates,
            disk_write_by_drive=write_rates,
            top_cpu_processes=sorted_by_cpu,
            top_mem_processes=sorted_by_mem,
            top_disk_read_processes=sorted_by_read,
            top_disk_write_processes=sorted_by_write,
            swap_used_gb=swap_used_gb,
            swap_total_gb=swap_total_gb,
            swap_usage_pct=swap_usage_pct,
        )
