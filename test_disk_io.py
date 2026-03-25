import psutil
import time

def test_disk():
    disk1 = psutil.disk_io_counters(perdisk=False)
    t1 = time.monotonic()
    
    # Do some disk IO
    with open("temp_disk_test.dat", "wb") as f:
        f.write(b"0" * (1024 * 1024 * 50)) # 50 MB
        f.flush()
        
    t2 = time.monotonic()
    disk2 = psutil.disk_io_counters(perdisk=False)
    
    dt = t2 - t1
    read_diff = disk2.read_time - disk1.read_time
    write_diff = disk2.write_time - disk1.write_time
    
    busy_ms = read_diff + write_diff
    
    print(f"Elapsed Time: {dt:.3f} sec")
    print(f"Read Time Diff: {read_diff} (units?)")
    print(f"Write Time Diff: {write_diff} (units?)")
    print(f"Busy Time: {busy_ms} (units?)")
    
    pct = (busy_ms / (dt * 1000.0)) * 100.0
    print(f"Calculated % if units are ms: {pct:.2f}%")
    print(f"Calculated % if units are fractions (missing * 100): {pct * 100:.2f}%")

if __name__ == '__main__':
    test_disk()
