# collector_main.py
import time
import sys
import traceback

import config
from collectors.models import WindowState
from collectors.sampler import Sampler
from collectors.aggregator import Aggregator
from collectors.writers import OutputsWriter

def main():
    print("Starting Python System Collector...")
    sampler = Sampler(top_n=config.TOP_N)
    aggregator = Aggregator(top_n=config.TOP_N)
    writer = OutputsWriter(output_dir=config.OUTPUT_DIR, encoding=config.CSV_ENCODING)
    
    window_sec = config.AGGREGATION_WINDOW_SEC
    interval_sec = config.SAMPLE_INTERVAL_SEC
    
    state = WindowState(window_start=time.time())
    
    print(f"Sampling every {interval_sec}s, Aggregating every {window_sec}s.")
    print(f"Output Directory: {config.OUTPUT_DIR}")
    
    next_tick = time.monotonic() + interval_sec
    
    while True:
        try:
            # 1. Sample
            sample = sampler.sample()
            state.update(sample)
            
            # 2. Check Window Boundary
            if state.sample_count >= window_sec:
                # 3. Aggregate
                res_row, proc_row, summary = aggregator.aggregate(state)
                
                # 4. Write
                writer.write_csv("resource", res_row)
                writer.write_csv("process", proc_row)
                if config.ENABLE_SUMMARY_LOG:
                    writer.write_summary(summary)
                    print(summary)
                    
                # 5. Reset State
                state.reset(new_start_time=time.time())
                
        except KeyboardInterrupt:
            print("\nCollector stopping cleanly.")
            break
        except Exception as e:
            # Master exception catcher so collector never dies
            print(f"Error in collector loop: {e}", file=sys.stderr)
            traceback.print_exc()
            
        # Drift-controlled sleep
        now = time.monotonic()
        sleep_time = next_tick - now
        if sleep_time > 0:
            time.sleep(sleep_time)
        next_tick += interval_sec

if __name__ == "__main__":
    main()
