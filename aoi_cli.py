import argparse
import sys
from pathlib import Path

from data_loader import load_data
from excel_exporter import generate_inspection_excel
from inspector_logs.core import (
    build_inspection_records,
    load_inspector_log_data,
    resolve_inspector_log_paths,
    select_inspection_records,
    summarize_inspection_records,
    summarize_inspector_log_data,
)


def _print_summary(path_input: list[str]) -> int:
    raw_paths = "\n".join(path_input)
    resolved_paths = resolve_inspector_log_paths(raw_paths)
    df = load_inspector_log_data(raw_paths)
    summary = summarize_inspector_log_data(df)
    inspection_records = build_inspection_records(df)
    inspection_summary = summarize_inspection_records(inspection_records)

    print(f"Resolved files: {len(resolved_paths)}")
    for path in resolved_paths:
        print(f" - {path}")

    print(f"Parsed rows: {summary['rows']}")
    print(f"InspTime rows: {summary['insp_rows']}")
    print(f"Working Set rows: {summary['memory_rows']}")
    print(f"Inspection records: {summary['inspection_rows']}")

    if summary["active_model_name"] is not None:
        print(f"Latest model: {summary['active_model_name']}")
    if inspection_summary["no_range"] is not None:
        start_no, end_no = inspection_summary["no_range"]
        print(f"NO range: {start_no} -> {end_no}")

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


def _resolve_selected_range(inspection_records, start_no: int | None, end_no: int | None):
    inspection_summary = summarize_inspection_records(inspection_records)
    if inspection_summary["rows"] == 0 or inspection_summary["no_range"] is None:
        return None, None, inspection_records

    min_no, max_no = inspection_summary["no_range"]
    selected_start = min_no if start_no is None else start_no
    selected_end = max_no if end_no is None else end_no

    if selected_start < min_no or selected_end > max_no or selected_start > selected_end:
        raise ValueError(f"Invalid NO range. Available range is {min_no} -> {max_no}.")

    return selected_start, selected_end, select_inspection_records(inspection_records, selected_start, selected_end)


def _load_system_monitor_data(system_paths: list[str] | None):
    if not system_paths:
        return None
    return load_data(system_paths)


def _export_inspection_results(
    aoi_paths: list[str],
    system_paths: list[str] | None,
    output_path: str,
    start_no: int | None,
    end_no: int | None,
    include_inspector_memory: bool,
) -> int:
    raw_paths = "\n".join(aoi_paths)
    resolved_paths = resolve_inspector_log_paths(raw_paths)
    if not resolved_paths:
        print("No AOI / Inspector logs were resolved.")
        return 1

    inspector_df = load_inspector_log_data(raw_paths)
    system_df = _load_system_monitor_data(system_paths)
    inspection_records = build_inspection_records(inspector_df, system_df)
    inspection_summary = summarize_inspection_records(inspection_records)

    if inspection_summary["rows"] == 0:
        print("No inspection records were reconstructed from the AOI / Inspector logs.")
        return 1

    try:
        selected_start, selected_end, selected_records = _resolve_selected_range(inspection_records, start_no, end_no)
    except ValueError as exc:
        print(exc)
        return 1

    output_file = Path(output_path).expanduser()
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(
        generate_inspection_excel(
            selected_records,
            include_inspector_memory=include_inspector_memory,
            sample_records=inspection_records,
        )
    )

    print(f"Resolved files: {len(resolved_paths)}")
    for path in resolved_paths:
        print(f" - {path}")

    if system_paths:
        print(f"System files: {len(system_paths)}")
        for path in system_paths:
            print(f" - {path}")

    if inspection_summary["primary_model_name"] is not None:
        print(f"Latest model: {inspection_summary['primary_model_name']}")
    print(f"Inspection records: {inspection_summary['rows']}")
    print(f"System memory matches: {inspection_summary['system_memory_matches']}")
    print(f"Export range: NO {selected_start} -> {selected_end}")
    print(f"Exported rows: {len(selected_records)}")
    print(f"Output: {output_file.resolve()}")

    return 0


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

    export_parser = subparsers.add_parser("export", help="Build numbered inspection results and export them as XLSX")
    export_parser.add_argument(
        "--path",
        dest="paths",
        action="append",
        required=True,
        help="AOI log file path, folder path, or a base path without extension. Repeat for multiple paths.",
    )
    export_parser.add_argument(
        "--system-path",
        dest="system_paths",
        action="append",
        help="System monitor CSV file path. Repeat for both resource/process files when system memory matching is needed.",
    )
    export_parser.add_argument(
        "--out",
        required=True,
        help="Output XLSX file path.",
    )
    export_parser.add_argument(
        "--start-no",
        type=int,
        help="First inspection NO to export. Defaults to 1.",
    )
    export_parser.add_argument(
        "--end-no",
        type=int,
        help="Last inspection NO to export. Defaults to the final available NO.",
    )
    export_parser.add_argument(
        "--include-inspector-memory",
        action="store_true",
        help="Include `메모리 (인스펙터)` to the right of `메모리 (시스템)` in the exported XLSX.",
    )

    args = parser.parse_args()

    if args.command == "summary":
        return _print_summary(args.paths)
    if args.command == "export":
        return _export_inspection_results(
            aoi_paths=args.paths,
            system_paths=args.system_paths,
            output_path=args.out,
            start_no=args.start_no,
            end_no=args.end_no,
            include_inspector_memory=args.include_inspector_memory,
        )

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
