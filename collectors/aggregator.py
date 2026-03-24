# collectors/aggregator.py
import datetime
from typing import Dict, Tuple
from collectors.models import WindowState

class Aggregator:
    def __init__(self, top_n=5):
        self.top_n = top_n

    def _format_top_n(self, proc_dict, is_mb=False):
        # Sort by value descending
        sorted_procs = sorted(proc_dict.items(), key=lambda x: x[1], reverse=True)[:self.top_n]
        tokens = []
        for name, val in sorted_procs:
            if is_mb:
                val = val / (1024 * 1024)
            tokens.append(f"{name}:{val:.1f}")
        return " | ".join(tokens)

    def aggregate(self, state: WindowState) -> Tuple[Dict, Dict, str]:
        if state.is_empty():
            return {}, {}, ""
            
        samples = state.samples
        count = len(samples)
        
        # Resource aggregation variables
        cpu_avg = sum(s.cpu_total for s in samples) / count
        cpu_peak = max(s.cpu_total for s in samples)
        mem_avg = sum(s.mem_usage_pct for s in samples) / count
        mem_gb_avg = sum(s.mem_used_gb for s in samples) / count
        
        # Disk IO aggregation (average of rates over the window, or peak? The prompt says peak/avg depending on metrics. Let's do max for rates to catch spikes, and avg for time.)
        # Actually, let's keep it simple: max for throughput, avg for active time.
        all_drives = set()
        for s in samples:
            all_drives.update(s.disk_time_by_drive.keys())
            
        disk_time_avg = {}
        disk_read_peak = {}
        disk_write_peak = {}
        
        for drive in all_drives:
            disk_time_avg[drive] = sum(s.disk_time_by_drive.get(drive, 0.0) for s in samples) / count
            disk_read_peak[drive] = max(s.disk_read_by_drive.get(drive, 0.0) for s in samples)
            disk_write_peak[drive] = max(s.disk_write_by_drive.get(drive, 0.0) for s in samples)
            
        # Process peak aggregation
        proc_cpu_peaks = {}
        proc_mem_peaks = {}
        proc_read_peaks = {}
        proc_write_peaks = {}
        
        for s in samples:
            for p in s.top_cpu_processes:
                proc_cpu_peaks[p['name']] = max(proc_cpu_peaks.get(p['name'], 0), p['cpu'])
            for p in s.top_mem_processes:
                proc_mem_peaks[p['name']] = max(proc_mem_peaks.get(p['name'], 0), p['mem_mb'] * 1024 * 1024) # Keep in bytes for formatting
            for p in s.top_disk_read_processes:
                proc_read_peaks[p['name']] = max(proc_read_peaks.get(p['name'], 0), p['read_rate'])
            for p in s.top_disk_write_processes:
                proc_write_peaks[p['name']] = max(proc_write_peaks.get(p['name'], 0), p['write_rate'])
                
        # Format Top 5 strings
        top_cpu_str = self._format_top_n(proc_cpu_peaks)
        top_mem_str = self._format_top_n(proc_mem_peaks, is_mb=True)
        top_read_str = self._format_top_n(proc_read_peaks, is_mb=True)
        top_write_str = self._format_top_n(proc_write_peaks, is_mb=True)
        
        # Combined Disk IO for processes (Read + Write)
        proc_io_peaks = {}
        for name in set(proc_read_peaks.keys()).union(proc_write_peaks.keys()):
            proc_io_peaks[name] = proc_read_peaks.get(name, 0) + proc_write_peaks.get(name, 0)
        top_io_str = self._format_top_n(proc_io_peaks, is_mb=True)

        # Timestamps
        ts_end = datetime.datetime.fromtimestamp(state.window_end).strftime('%Y-%m-%d %H:%M:%S')

        # Resource Row
        resource_row = {
            'Timestamp': ts_end,
            'CPU_Avg(%)': cpu_avg,
            'CPU_Peak(%)': cpu_peak,
            'Mem_Used(GB)': mem_gb_avg,
            'Mem_Usage_Avg(%)': mem_avg,
            'SampleCount': count
        }
        for drive in all_drives:
            resource_row[f'DiskTime_{drive}(%)'] = disk_time_avg[drive]
            resource_row[f'DiskRead_{drive}(B/s)'] = disk_read_peak[drive]
            resource_row[f'DiskWrite_{drive}(B/s)'] = disk_write_peak[drive]
            
        # Process Row
        process_row = {
            'Timestamp': ts_end,
            'Top5_CPU(%)': top_cpu_str,
            'Top5_Memory_MB': top_mem_str,
            'Top5_Disk_Read_MBs': top_read_str,
            'Top5_Disk_Write_MBs': top_write_str,
            'Top5_Disk_IO_Global(MB/s)': top_io_str,
            'SampleCount': count
        }
        
        # Summary String
        summary_line = f"[{ts_end}] CPU Avg:{cpu_avg:5.1f}% Peak:{cpu_peak:5.1f}% | Mem:{mem_gb_avg:5.2f}GB ({mem_avg:5.1f}%) | Top CPU: {top_cpu_str[:30]}..."

        return resource_row, process_row, summary_line
