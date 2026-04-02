import argparse
import sys
import config
from collectors.core import MonitorEngine
from collectors.cpu_temperature import CpuTemperatureProbe

def main():
    parser = argparse.ArgumentParser(description="System Resource Monitor CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    start_parser = subparsers.add_parser("start", help="Start the collector")
    start_parser.add_argument("--out-dir", type=str, default=config.OUTPUT_DIR, help="Output directory for logs")
    start_parser.add_argument("--interval", type=int, default=config.SAMPLE_INTERVAL_SEC, help="Sampling interval in seconds")
    start_parser.add_argument("--window", type=int, default=config.AGGREGATION_WINDOW_SEC, help="Aggregation window in seconds")
    start_parser.add_argument("--iterations", type=int, default=None, help="Stop after N sampling iterations (for testing)")

    probe_temp_parser = subparsers.add_parser("probe-temp", help="Probe CPU temperature sensor availability")
    probe_temp_parser.add_argument("--retry-interval", type=float, default=0.0, help="Retry interval in seconds for sensor detection")
    
    args = parser.parse_args()
    
    if args.command == "start":
        engine = MonitorEngine(
            output_dir=args.out_dir,
            interval_sec=args.interval,
            window_sec=args.window
        )
        engine.run(max_iterations=args.iterations)
    elif args.command == "probe-temp":
        probe = CpuTemperatureProbe(retry_interval_sec=args.retry_interval)
        value = probe.read_celsius(force_refresh=True)
        source = probe.source_name or "Unavailable"
        if value is None:
            print(f"CPU temperature sensor not available. Source: {source}")
            sys.exit(1)
        print(f"CPU temperature: {value:.1f}°C (Source: {source})")
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
