import argparse
import sys

from inspector_logs.core import load_inspector_log_data, resolve_inspector_log_paths, summarize_inspector_log_data


def _print_summary(path_input: list[str]) -> int:
    raw_paths = "\n".join(path_input)
    resolved_paths = resolve_inspector_log_paths(raw_paths)
    df = load_inspector_log_data(raw_paths)
    summary = summarize_inspector_log_data(df)

    print(f"Resolved files: {len(resolved_paths)}")
    for path in resolved_paths:
        print(f" - {path}")

    print(f"Parsed rows: {summary['rows']}")
    print(f"InspTime rows: {summary['insp_rows']}")
    print(f"Working Set rows: {summary['memory_rows']}")

    if summary["time_range"] is not None:
        start_ts, end_ts = summary["time_range"]
        print(f"Time range: {start_ts} -> {end_ts}")

    if summary["max_frame_sec"] is not None:
        print(f"Peak frame inspect time: {summary['max_frame_sec']:.2f} sec")
    if summary["max_total_sec"] is not None:
        print(f"Peak total inspect time: {summary['max_total_sec']:.2f} sec")
    if summary["max_working_set_gb"] is not None:
        print(f"Peak working set (log unit KB -> GB): {summary['max_working_set_gb']:.2f} GB")

    return 0 if summary["rows"] > 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="AOI / Inspector log utility")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    summary_parser = subparsers.add_parser("summary", help="Parse AOI logs and print a smoke-test friendly summary")
    summary_parser.add_argument(
        "--path",
        dest="paths",
        action="append",
        required=True,
        help="AOI log file path, folder path, or a base path without extension. Repeat for multiple paths.",
    )

    args = parser.parse_args()

    if args.command == "summary":
        return _print_summary(args.paths)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
