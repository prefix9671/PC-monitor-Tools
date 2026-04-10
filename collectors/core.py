import time
import sys
import traceback
from datetime import datetime

import config
from collectors.models import WindowState
from collectors.sampler import Sampler
from collectors.aggregator import Aggregator
from collectors.writers import OutputsWriter

class MonitorEngine:
    def __init__(self, output_dir, interval_sec=1, window_sec=5):
        self.interval_sec = interval_sec
        self.window_sec = window_sec
        
        self.sampler = Sampler(top_n=config.TOP_N)
        self.aggregator = Aggregator(top_n=config.TOP_N)
        self.writer = OutputsWriter(output_dir=output_dir, encoding=config.CSV_ENCODING)
        
        print(f"Starting MonitorEngine (Interval: {self.interval_sec}s, Window: {self.window_sec}s)")
        print(f"Output Directory: {output_dir}")
        
    def run(self, max_iterations=None):
        state = WindowState(window_start=time.time())
        next_tick = time.monotonic() + self.interval_sec
        iteration_count = 0
        
        try:
            while True:
                if max_iterations is not None and iteration_count >= max_iterations:
                    break
                    
                # 1. Sample
                sample = self.sampler.sample()
                state.update(sample)
                iteration_count += 1
                
                # 2. Check Window Boundary
                if state.sample_count >= self.window_sec:
                    # 3. Aggregate
                    res_row, proc_row, summary = self.aggregator.aggregate(state)
                    
                    # 4. Write
                    self.writer.write_csv("resource", res_row)
                    self.writer.write_csv("process", proc_row)
                    if config.ENABLE_SUMMARY_LOG:
                        self.writer.write_summary(summary)
                        print(f"[{datetime.now()}] Wrote {self.window_sec}s aggregated data.")
                        
                    # 5. Reset State
                    state.reset(new_start_time=time.time())
                
                # Drift-controlled sleep
                now = time.monotonic()
                sleep_time = next_tick - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                next_tick += self.interval_sec
                
        except KeyboardInterrupt:
            print("\nCollector stopping cleanly.")
        except Exception as e:
            print(f"Error in collector loop: {e}", file=sys.stderr)
            traceback.print_exc()
        finally:
            self.sampler.close()
