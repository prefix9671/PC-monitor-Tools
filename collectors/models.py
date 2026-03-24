# collectors/models.py
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class MetricSample:
    """Represents a single 1-second sample from psutil."""
    timestamp: float
    cpu_total: float
    mem_used_gb: float
    mem_usage_pct: float
    disk_time_by_drive: Dict[str, float]
    disk_read_by_drive: Dict[str, float]
    disk_write_by_drive: Dict[str, float]
    
    top_cpu_processes: List[Dict]
    top_mem_processes: List[Dict]
    top_disk_read_processes: List[Dict]
    top_disk_write_processes: List[Dict]

@dataclass
class WindowState:
    """Holds accumulated samples over an aggregation window."""
    window_start: float
    window_end: Optional[float] = None
    sample_count: int = 0
    
    samples: List[MetricSample] = field(default_factory=list)

    def update(self, sample: MetricSample):
        self.samples.append(sample)
        self.sample_count += 1
        self.window_end = sample.timestamp

    def reset(self, new_start_time: float):
        self.window_start = new_start_time
        self.window_end = None
        self.sample_count = 0
        self.samples.clear()
        
    def is_empty(self):
        return self.sample_count == 0
