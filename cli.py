import argparse
import sys
import config
from collectors.core import MonitorEngine

def main():
    parser = argparse.ArgumentParser(description="System Resource Monitor CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    start_parser = subparsers.add_parser("start", help="Start the collector")
    start_parser.add_argument("--out-dir", type=str, default=config.OUTPUT_DIR, help="Output directory for logs")
    start_parser.add_argument("--interval", type=int, default=config.SAMPLE_INTERVAL_SEC, help="Sampling interval in seconds")
    start_parser.add_argument("--window", type=int, default=config.AGGREGATION_WINDOW_SEC, help="Aggregation window in seconds")
    start_parser.add_argument("--iterations", type=int, default=None, help="Stop after N sampling iterations (for testing)")
    
    args = parser.parse_args()
    
    if args.command == "start":
        engine = MonitorEngine(
            output_dir=args.out_dir,
            interval_sec=args.interval,
            window_sec=args.window
        )
        engine.run(max_iterations=args.iterations)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
