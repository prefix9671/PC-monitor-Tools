from __future__ import annotations

import concurrent.futures
import io
import os
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from inspector_logs.spi_parser import parse_spi_rows
from inspector_logs.text_utils import decode_text_lines

INSPECTOR_PROCESS_LABEL = "인스펙터 앱 (로그)"
SUPPORTED_LOG_SUFFIXES = (".log", ".txt", ".csv")
INSPECTOR_PARSE_CHUNK_LINE_COUNT = 250_000
INSPECTOR_PARSE_MIN_LINE_COUNT_FOR_PARALLEL = 500_000
INSPECTOR_PARSE_MAX_WORKERS = 8

INSPTIME_PATTERN = re.compile(
    r"(?P<stamp>\d{8}_\d{6}).*?\|InspTime\|"
    r"Frame\s*:\s*(?P<frame_sec>[\d.]+)\s*sec\|"
    r"Total\s*:\s*(?P<total_sec>[\d.]+)\s*sec\s*/\s*(?P<frame_count>\d+)\s*frame",
    re.IGNORECASE,
)

WORKING_SET_PATTERN = re.compile(
    r"(?P<stamp>\d{8}_\d{6}).*?\|Memory\|Working Set Memory Size\s*\|\s*(?P<working_set_kb>\d+)\s*KB",
    re.IGNORECASE,
)

MODEL_OPEN_PATTERN = re.compile(
    r"(?P<stamp>\d{8}_\d{6}).*?Model Open\s*:\s*(?P<model_name>.+?)(?:\s*\|.*)?$",
    re.IGNORECASE,
)

INSPECTOR_COLUMNS = [
    "Timestamp",
    "SourceFile",
    "Inspector_Event_Type",
    "Inspector_Source_Type",
    "Inspector_Memory_Key",
    "Inspector_Model_Name",
    "Inspector_Frame_Sec",
    "Inspector_Total_Sec",
    "Inspector_Total_Frames",
    "Inspector_WorkingSet_KB",
    "Inspector_WorkingSet_MB",
    "Inspector_WorkingSet_GB",
]

INSPECTION_RECORD_COLUMNS = [
    "Timestamp",
    "SourceFile",
    "Inspector_Source_Type",
    "Inspection_No",
    "Inspector_Model_Name",
    "Inspector_Frame_Sec",
    "Inspector_Total_Sec",
    "Inspector_Total_Frames",
    "Inspector_WorkingSet_KB",
    "Inspector_WorkingSet_MB",
    "Inspector_WorkingSet_GB",
    "System_Memory_Used_GB",
    "System_Memory_Timestamp",
]

INSPECTION_PREVIEW_COLUMNS = {
    "Inspection_No": "NO",
    "Inspector_Frame_Sec": "Frame",
    "Inspector_Total_Sec": "Total",
    "Inspector_WorkingSet_GB": "메모리 (인스펙터)",
    "System_Memory_Used_GB": "메모리 (시스템)",
}

INSPECTION_EXPORT_BASE_COLUMNS = [
    "Inspection_No",
    "Inspector_Frame_Sec",
    "Inspector_Total_Sec",
    "System_Memory_Used_GB",
]

INSPECTION_SAMPLE_EXPORT_BASE_COLUMNS = [
    "Timestamp",
    "Inspection_No",
    "Inspector_Frame_Sec",
    "Inspector_Total_Sec",
    "System_Memory_Used_GB",
]


def _normalize_datetime_series(series: pd.Series) -> pd.Series:
    normalized = pd.to_datetime(series, errors="coerce")
    if normalized.empty:
        return normalized
    return normalized.astype("datetime64[ns]")


def _split_path_input(path_input: str | Iterable[str] | None) -> list[str]:
    if path_input is None:
        return []

    if isinstance(path_input, (list, tuple, set)):
        tokens = [str(item) for item in path_input]
    else:
        tokens = str(path_input).replace(";", "\n").splitlines()

    cleaned = []
    for token in tokens:
        normalized = token.strip().strip('"').strip("'")
        if normalized:
            cleaned.append(normalized)
    return cleaned


def _resolve_single_path(raw_path: str) -> list[Path]:
    candidate = Path(raw_path)

    if candidate.exists():
        if candidate.is_file():
            return [candidate]
        if candidate.is_dir():
            return sorted(
                [
                    child
                    for child in candidate.rglob("*")
                    if child.is_file() and child.suffix.lower() in SUPPORTED_LOG_SUFFIXES
                ],
                key=lambda path: str(path).lower(),
            )

    if candidate.suffix:
        return []

    resolved = []
    for suffix in SUPPORTED_LOG_SUFFIXES:
        with_suffix = Path(f"{raw_path}{suffix}")
        if with_suffix.exists() and with_suffix.is_file():
            resolved.append(with_suffix)
    return resolved


def resolve_inspector_log_paths(path_input: str | Iterable[str] | None) -> list[Path]:
    resolved: list[Path] = []
    seen: set[str] = set()

    for raw_path in _split_path_input(path_input):
        for resolved_path in _resolve_single_path(raw_path):
            normalized = str(resolved_path.resolve()).lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            resolved.append(resolved_path.resolve())

    return sorted(resolved, key=lambda path: str(path).lower())


def load_inspector_log_payloads(path_input: str | Iterable[str] | None) -> list[tuple[str, bytes]]:
    payloads: list[tuple[str, bytes]] = []
    for path in resolve_inspector_log_paths(path_input):
        payloads.append((path.name, path.read_bytes()))
    return payloads


def _build_unique_archive_member_name(file_name: str, used_names: set[str]) -> str:
    normalized_name = Path(file_name).name or "operation.txt"
    if normalized_name.lower() not in used_names:
        used_names.add(normalized_name.lower())
        return normalized_name

    base_name = Path(normalized_name).stem or "operation"
    suffix = Path(normalized_name).suffix or ".txt"
    index = 2
    while True:
        candidate = f"{base_name}_{index}{suffix}"
        if candidate.lower() not in used_names:
            used_names.add(candidate.lower())
            return candidate
        index += 1


def build_inspector_raw_download_artifact(
    payloads: Iterable[tuple[str, bytes]],
) -> dict[str, object] | None:
    normalized_payloads: list[tuple[str, bytes]] = []
    seen_payloads: set[tuple[str, bytes]] = set()
    for file_name, raw_bytes in payloads:
        if raw_bytes is None:
            continue
        normalized_name = Path(file_name).name or "operation.txt"
        payload_key = (normalized_name.lower(), raw_bytes)
        if payload_key in seen_payloads:
            continue
        seen_payloads.add(payload_key)
        normalized_payloads.append((normalized_name, raw_bytes))

    if not normalized_payloads:
        return None

    if len(normalized_payloads) == 1:
        file_name, raw_bytes = normalized_payloads[0]
        return {
            "file_name": file_name,
            "data": raw_bytes,
            "mime": "text/plain",
        }

    buffer = io.BytesIO()
    used_names: set[str] = set()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_name, raw_bytes in normalized_payloads:
            archive.writestr(_build_unique_archive_member_name(file_name, used_names), raw_bytes)

    return {
        "file_name": f"inspector_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
        "data": buffer.getvalue(),
        "mime": "application/zip",
    }


def _read_text_lines(path: Path) -> list[str]:
    raw_bytes = path.read_bytes()
    return _decode_text_lines(raw_bytes)


def _decode_text_lines(raw_bytes: bytes) -> list[str]:
    return decode_text_lines(raw_bytes)


def _parse_line(line: str, source_file: str) -> dict[str, object] | None:
    model_match = MODEL_OPEN_PATTERN.search(line)
    if model_match:
        return {
            "Timestamp": pd.to_datetime(model_match.group("stamp"), format="%Y%m%d_%H%M%S", errors="coerce"),
            "SourceFile": source_file,
            "Inspector_Event_Type": "model_open",
            "Inspector_Source_Type": "AOI",
            "Inspector_Memory_Key": source_file,
            "Inspector_Model_Name": model_match.group("model_name").strip().strip('"').strip("'"),
            "Inspector_Frame_Sec": pd.NA,
            "Inspector_Total_Sec": pd.NA,
            "Inspector_Total_Frames": pd.NA,
            "Inspector_WorkingSet_KB": pd.NA,
            "Inspector_WorkingSet_MB": pd.NA,
            "Inspector_WorkingSet_GB": pd.NA,
        }

    insp_match = INSPTIME_PATTERN.search(line)
    if insp_match:
        return {
            "Timestamp": pd.to_datetime(insp_match.group("stamp"), format="%Y%m%d_%H%M%S", errors="coerce"),
            "SourceFile": source_file,
            "Inspector_Event_Type": "insp_time",
            "Inspector_Source_Type": "AOI",
            "Inspector_Memory_Key": source_file,
            "Inspector_Model_Name": pd.NA,
            "Inspector_Frame_Sec": float(insp_match.group("frame_sec")),
            "Inspector_Total_Sec": float(insp_match.group("total_sec")),
            "Inspector_Total_Frames": int(insp_match.group("frame_count")),
            "Inspector_WorkingSet_KB": pd.NA,
            "Inspector_WorkingSet_MB": pd.NA,
            "Inspector_WorkingSet_GB": pd.NA,
        }

    mem_match = WORKING_SET_PATTERN.search(line)
    if mem_match:
        working_set_kb = float(mem_match.group("working_set_kb"))
        return {
            "Timestamp": pd.to_datetime(mem_match.group("stamp"), format="%Y%m%d_%H%M%S", errors="coerce"),
            "SourceFile": source_file,
            "Inspector_Event_Type": "working_set",
            "Inspector_Source_Type": "AOI",
            "Inspector_Memory_Key": source_file,
            "Inspector_Model_Name": pd.NA,
            "Inspector_Frame_Sec": pd.NA,
            "Inspector_Total_Sec": pd.NA,
            "Inspector_Total_Frames": pd.NA,
            "Inspector_WorkingSet_KB": working_set_kb,
            "Inspector_WorkingSet_MB": working_set_kb / 1024.0,
            "Inspector_WorkingSet_GB": working_set_kb / (1024.0 * 1024.0),
        }

    return None


def _parse_lines_chunk(lines: list[str], source_file: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in lines:
        normalized_line = line.lower()
        if (
            "|insptime|" not in normalized_line
            and "working set memory size" not in normalized_line
            and "model open" not in normalized_line
        ):
            continue
        parsed = _parse_line(line, source_file)
        if parsed is not None:
            rows.append(parsed)
    return rows


def _parse_lines_chunk_task(task: tuple[list[str], str]) -> list[dict[str, object]]:
    chunk_lines, source_file = task
    return _parse_lines_chunk(chunk_lines, source_file)


def _resolve_parse_worker_count(work_item_count: int) -> int:
    cpu_count = os.cpu_count() or 1
    return min(INSPECTOR_PARSE_MAX_WORKERS, cpu_count, max(1, work_item_count))


def _load_rows_from_text_lines(
    lines: list[str],
    source_file: str,
    allow_parallel_chunks: bool = True,
) -> list[dict[str, object]]:
    if not lines:
        return []

    rows: list[dict[str, object]] = []
    rows.extend(parse_spi_rows(lines, source_file))

    if (
        not allow_parallel_chunks
        or len(lines) < INSPECTOR_PARSE_MIN_LINE_COUNT_FOR_PARALLEL
    ):
        rows.extend(_parse_lines_chunk(lines, source_file))
        return rows

    chunk_count = (len(lines) + INSPECTOR_PARSE_CHUNK_LINE_COUNT - 1) // INSPECTOR_PARSE_CHUNK_LINE_COUNT
    max_workers = _resolve_parse_worker_count(chunk_count)
    if chunk_count < 2 or max_workers < 2:
        rows.extend(_parse_lines_chunk(lines, source_file))
        return rows

    tasks = (
        (lines[index:index + INSPECTOR_PARSE_CHUNK_LINE_COUNT], source_file)
        for index in range(0, len(lines), INSPECTOR_PARSE_CHUNK_LINE_COUNT)
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for chunk_rows in executor.map(_parse_lines_chunk_task, tasks):
            rows.extend(chunk_rows)
    return rows


def _load_rows_from_path(log_path: Path, allow_parallel_chunks: bool = True) -> list[dict[str, object]]:
    return _load_rows_from_text_lines(
        _read_text_lines(log_path),
        log_path.name,
        allow_parallel_chunks=allow_parallel_chunks,
    )


def _load_rows_from_path_task(task: tuple[Path, bool]) -> list[dict[str, object]]:
    log_path, allow_parallel_chunks = task
    return _load_rows_from_path(log_path, allow_parallel_chunks=allow_parallel_chunks)


def _load_rows_from_uploaded_file(
    file_name: str,
    raw_bytes: bytes,
    allow_parallel_chunks: bool = True,
) -> list[dict[str, object]]:
    return _load_rows_from_text_lines(
        _decode_text_lines(raw_bytes),
        file_name,
        allow_parallel_chunks=allow_parallel_chunks,
    )


def _load_rows_from_uploaded_file_task(task: tuple[str, bytes, bool]) -> list[dict[str, object]]:
    file_name, raw_bytes, allow_parallel_chunks = task
    return _load_rows_from_uploaded_file(
        file_name,
        raw_bytes,
        allow_parallel_chunks=allow_parallel_chunks,
    )


def load_inspector_log_data(path_input: str | Iterable[str] | None) -> pd.DataFrame:
    resolved_paths = resolve_inspector_log_paths(path_input)
    rows: list[dict[str, object]] = []

    if len(resolved_paths) <= 1:
        for log_path in resolved_paths:
            rows.extend(_load_rows_from_path(log_path, allow_parallel_chunks=True))
        return _rows_to_dataframe(rows)

    max_workers = _resolve_parse_worker_count(len(resolved_paths))
    if max_workers < 2:
        for log_path in resolved_paths:
            rows.extend(_load_rows_from_path(log_path, allow_parallel_chunks=False))
        return _rows_to_dataframe(rows)

    tasks = [(log_path, False) for log_path in resolved_paths]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for file_rows in executor.map(_load_rows_from_path_task, tasks):
            rows.extend(file_rows)

    return _rows_to_dataframe(rows)


def load_inspector_log_data_from_uploads(uploaded_files: Iterable[tuple[str, bytes]] | None) -> pd.DataFrame:
    uploaded_file_list = list(uploaded_files or [])
    rows: list[dict[str, object]] = []

    if len(uploaded_file_list) <= 1:
        for file_name, raw_bytes in uploaded_file_list:
            rows.extend(_load_rows_from_uploaded_file(file_name, raw_bytes, allow_parallel_chunks=True))
        return _rows_to_dataframe(rows)

    max_workers = _resolve_parse_worker_count(len(uploaded_file_list))
    if max_workers < 2:
        for file_name, raw_bytes in uploaded_file_list:
            rows.extend(_load_rows_from_uploaded_file(file_name, raw_bytes, allow_parallel_chunks=False))
        return _rows_to_dataframe(rows)

    tasks = [(file_name, raw_bytes, False) for file_name, raw_bytes in uploaded_file_list]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for file_rows in executor.map(_load_rows_from_uploaded_file_task, tasks):
            rows.extend(file_rows)

    return _rows_to_dataframe(rows)


def _rows_to_dataframe(rows: list[dict[str, object]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=INSPECTOR_COLUMNS)

    df = pd.DataFrame(rows, columns=INSPECTOR_COLUMNS)
    df["Timestamp"] = _normalize_datetime_series(df["Timestamp"])
    df["Inspector_Source_Type"] = df["Inspector_Source_Type"].fillna("AOI")
    df["Inspector_Memory_Key"] = df["Inspector_Memory_Key"].fillna(df["SourceFile"])
    return (
        df.dropna(subset=["Timestamp"])
        .sort_values("Timestamp", kind="mergesort")
        .reset_index(drop=True)
    )


def _empty_inspection_records() -> pd.DataFrame:
    return pd.DataFrame(columns=INSPECTION_RECORD_COLUMNS)


def _ordered_unique_non_empty(values: Iterable[object]) -> list[str]:
    ordered_values: list[str] = []
    seen: set[str] = set()

    for value in values:
        if pd.isna(value):
            continue
        normalized = str(value).strip()
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered_values.append(normalized)

    return ordered_values


def build_inspection_records(inspector_df: pd.DataFrame, system_df: pd.DataFrame | None = None) -> pd.DataFrame:
    if inspector_df is None or inspector_df.empty or "Timestamp" not in inspector_df.columns:
        return _empty_inspection_records()

    events = inspector_df.copy()
    events["Timestamp"] = _normalize_datetime_series(events["Timestamp"])
    events = (
        events.dropna(subset=["Timestamp"])
        .sort_values("Timestamp", kind="mergesort")
        .reset_index(drop=True)
    )

    if events.empty:
        return _empty_inspection_records()

    events["_EventOrder"] = range(len(events))

    insp_rows = events.loc[
        events["Inspector_Event_Type"] == "insp_time",
        [
            "Timestamp",
            "SourceFile",
            "Inspector_Source_Type",
            "Inspector_Memory_Key",
            "Inspector_Model_Name",
            "Inspector_Frame_Sec",
            "Inspector_Total_Sec",
            "Inspector_Total_Frames",
            "_EventOrder",
        ],
    ].copy()

    if insp_rows.empty:
        return _empty_inspection_records()

    insp_rows["Inspection_Order"] = range(len(insp_rows))
    insp_rows = (
        insp_rows.sort_values(["SourceFile", "Timestamp", "_EventOrder"], kind="mergesort")
        .reset_index(drop=True)
    )

    model_rows = events.loc[
        events["Inspector_Event_Type"] == "model_open",
        ["Timestamp", "SourceFile", "Inspector_Model_Name", "_EventOrder"],
    ].copy()
    model_rows = model_rows.dropna(subset=["Inspector_Model_Name"])

    if not model_rows.empty:
        model_rows = model_rows.sort_values(["SourceFile", "Timestamp", "_EventOrder"], kind="mergesort")
        insp_rows = pd.merge_asof(
            insp_rows,
            model_rows[["Timestamp", "SourceFile", "Inspector_Model_Name"]].rename(
                columns={"Inspector_Model_Name": "_Merged_Model_Name"}
            ),
            on="Timestamp",
            by="SourceFile",
            direction="backward",
            allow_exact_matches=True,
        )
        insp_rows["Inspector_Model_Name"] = insp_rows["Inspector_Model_Name"].combine_first(
            insp_rows["_Merged_Model_Name"]
        )
        insp_rows = insp_rows.drop(columns=["_Merged_Model_Name"])
    else:
        insp_rows["Inspector_Model_Name"] = insp_rows["Inspector_Model_Name"].fillna(pd.NA)

    memory_rows = events.loc[
        events["Inspector_Event_Type"] == "working_set",
        [
            "Timestamp",
            "SourceFile",
            "Inspector_Memory_Key",
            "Inspector_WorkingSet_KB",
            "Inspector_WorkingSet_MB",
            "Inspector_WorkingSet_GB",
            "_EventOrder",
        ],
    ].copy()

    if not memory_rows.empty:
        memory_rows = memory_rows.sort_values(["Inspector_Memory_Key", "Timestamp", "_EventOrder"], kind="mergesort")
        insp_rows = insp_rows.sort_values(["Inspector_Memory_Key", "Timestamp", "_EventOrder"], kind="mergesort")
        insp_rows = pd.merge_asof(
            insp_rows,
            memory_rows[
                [
                    "Timestamp",
                    "Inspector_Memory_Key",
                    "Inspector_WorkingSet_KB",
                    "Inspector_WorkingSet_MB",
                    "Inspector_WorkingSet_GB",
                ]
            ],
            on="Timestamp",
            by="Inspector_Memory_Key",
            direction="backward",
            allow_exact_matches=True,
        )
    else:
        insp_rows["Inspector_WorkingSet_KB"] = pd.NA
        insp_rows["Inspector_WorkingSet_MB"] = pd.NA
        insp_rows["Inspector_WorkingSet_GB"] = pd.NA

    records = (
        insp_rows.sort_values("Inspection_Order", kind="mergesort")
        .reset_index(drop=True)
    )
    records["Inspection_No"] = range(1, len(records) + 1)
    records = records.drop(columns=["_EventOrder", "Inspection_Order"], errors="ignore")

    if system_df is not None and not system_df.empty and {"Timestamp", "Mem_Used(GB)"}.issubset(system_df.columns):
        system_memory = system_df[["Timestamp", "Mem_Used(GB)"]].copy()
        system_memory["Timestamp"] = _normalize_datetime_series(system_memory["Timestamp"])
        system_memory["Mem_Used(GB)"] = pd.to_numeric(system_memory["Mem_Used(GB)"], errors="coerce")
        system_memory = (
            system_memory.dropna(subset=["Timestamp", "Mem_Used(GB)"])
            .sort_values("Timestamp", kind="mergesort")
            .rename(
                columns={
                    "Timestamp": "System_Memory_Timestamp",
                    "Mem_Used(GB)": "System_Memory_Used_GB",
                }
            )
        )

        if not system_memory.empty:
            records = pd.merge_asof(
                records.sort_values("Timestamp", kind="mergesort"),
                system_memory,
                left_on="Timestamp",
                right_on="System_Memory_Timestamp",
                direction="backward",
                allow_exact_matches=False,
            )
        else:
            records["System_Memory_Used_GB"] = pd.NA
            records["System_Memory_Timestamp"] = pd.NaT
    else:
        records["System_Memory_Used_GB"] = pd.NA
        records["System_Memory_Timestamp"] = pd.NaT

    for column in INSPECTION_RECORD_COLUMNS:
        if column not in records.columns:
            records[column] = pd.NA

    return records[INSPECTION_RECORD_COLUMNS].reset_index(drop=True)


def select_inspection_records(
    inspection_records: pd.DataFrame,
    start_no: int | None = None,
    end_no: int | None = None,
) -> pd.DataFrame:
    if inspection_records is None or inspection_records.empty or "Inspection_No" not in inspection_records.columns:
        return _empty_inspection_records()

    selected = inspection_records.copy()
    if start_no is not None:
        selected = selected[selected["Inspection_No"] >= int(start_no)]
    if end_no is not None:
        selected = selected[selected["Inspection_No"] <= int(end_no)]

    return selected.reset_index(drop=True)


def filter_inspection_records_by_time_range(
    inspection_records: pd.DataFrame,
    start_time: object | None = None,
    end_time: object | None = None,
) -> pd.DataFrame:
    if inspection_records is None or inspection_records.empty or "Timestamp" not in inspection_records.columns:
        return _empty_inspection_records()

    filtered = inspection_records.copy()
    filtered["Timestamp"] = _normalize_datetime_series(filtered["Timestamp"])
    filtered = filtered.dropna(subset=["Timestamp"])

    if start_time is not None:
        resolved_start = pd.Timestamp(start_time)
        filtered = filtered[filtered["Timestamp"] >= resolved_start]
    if end_time is not None:
        resolved_end = pd.Timestamp(end_time)
        filtered = filtered[filtered["Timestamp"] <= resolved_end]

    return filtered.reset_index(drop=True)


def _format_elapsed_time_korean(delta: pd.Timedelta) -> str:
    if pd.isna(delta):
        return "0분"

    total_seconds = max(int(delta.total_seconds()), 0)
    total_minutes = total_seconds // 60
    days, remaining_minutes = divmod(total_minutes, 24 * 60)
    hours, minutes = divmod(remaining_minutes, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}일")
    if hours:
        parts.append(f"{hours}시간")
    if minutes or not parts:
        parts.append(f"{minutes}분")
    return " ".join(parts)


def resolve_inspection_sample_time_window(
    inspection_records: pd.DataFrame,
    start_time: object | None = None,
    end_time: object | None = None,
) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
    if start_time is not None:
        resolved_start = pd.Timestamp(start_time)
    elif inspection_records is not None and not inspection_records.empty and "Timestamp" in inspection_records.columns:
        resolved_start = pd.to_datetime(inspection_records["Timestamp"], errors="coerce").dropna().min()
    else:
        resolved_start = None

    if end_time is not None:
        resolved_end = pd.Timestamp(end_time)
    elif inspection_records is not None and not inspection_records.empty and "Timestamp" in inspection_records.columns:
        resolved_end = pd.to_datetime(inspection_records["Timestamp"], errors="coerce").dropna().max()
    else:
        resolved_end = None

    return resolved_start, resolved_end


def _format_inspection_dataframe(
    inspection_records: pd.DataFrame,
    selected_columns: list[str],
    renamed_columns: dict[str, str],
) -> pd.DataFrame:
    if inspection_records is None or inspection_records.empty:
        return pd.DataFrame(columns=list(renamed_columns.values()))

    export_df = inspection_records[selected_columns].copy()
    if "Timestamp" in export_df.columns:
        export_df["Timestamp"] = _normalize_datetime_series(export_df["Timestamp"])
    if "Inspection_No" in export_df.columns:
        export_df["Inspection_No"] = pd.to_numeric(export_df["Inspection_No"], errors="coerce").astype("Int64")
    if "Inspector_Frame_Sec" in export_df.columns:
        export_df["Inspector_Frame_Sec"] = pd.to_numeric(export_df["Inspector_Frame_Sec"], errors="coerce").round(2)
    if "Inspector_Total_Sec" in export_df.columns:
        export_df["Inspector_Total_Sec"] = pd.to_numeric(export_df["Inspector_Total_Sec"], errors="coerce").round(2)
    if "Inspector_WorkingSet_GB" in export_df.columns:
        export_df["Inspector_WorkingSet_GB"] = pd.to_numeric(export_df["Inspector_WorkingSet_GB"], errors="coerce").round(3)
    if "System_Memory_Used_GB" in export_df.columns:
        export_df["System_Memory_Used_GB"] = pd.to_numeric(export_df["System_Memory_Used_GB"], errors="coerce").round(3)
    return export_df.rename(columns=renamed_columns)


def format_inspection_preview_dataframe(inspection_records: pd.DataFrame) -> pd.DataFrame:
    return _format_inspection_dataframe(
        inspection_records=inspection_records,
        selected_columns=list(INSPECTION_PREVIEW_COLUMNS.keys()),
        renamed_columns=INSPECTION_PREVIEW_COLUMNS,
    )


def format_inspection_export_dataframe(
    inspection_records: pd.DataFrame,
    include_inspector_memory: bool = False,
) -> pd.DataFrame:
    selected_columns = INSPECTION_EXPORT_BASE_COLUMNS.copy()
    renamed_columns = {
        "Inspection_No": "NO",
        "Inspector_Frame_Sec": "Frame",
        "Inspector_Total_Sec": "Total",
        "System_Memory_Used_GB": "메모리 (시스템)",
    }

    if include_inspector_memory:
        selected_columns.append("Inspector_WorkingSet_GB")
        renamed_columns["Inspector_WorkingSet_GB"] = "메모리 (인스펙터)"

    return _format_inspection_dataframe(
        inspection_records=inspection_records,
        selected_columns=selected_columns,
        renamed_columns=renamed_columns,
    )


def format_inspection_sample_dataframe(
    inspection_records: pd.DataFrame,
    include_inspector_memory: bool = False,
) -> pd.DataFrame:
    selected_columns = INSPECTION_SAMPLE_EXPORT_BASE_COLUMNS.copy()
    renamed_columns = {
        "Timestamp": "Timestamp",
        "Inspection_No": "NO",
        "Inspector_Frame_Sec": "Frame",
        "Inspector_Total_Sec": "Total",
        "System_Memory_Used_GB": "메모리 (시스템)",
    }

    if include_inspector_memory:
        selected_columns.append("Inspector_WorkingSet_GB")
        renamed_columns["Inspector_WorkingSet_GB"] = "메모리 (인스펙터)"

    return _format_inspection_dataframe(
        inspection_records=inspection_records,
        selected_columns=selected_columns,
        renamed_columns=renamed_columns,
    )


def build_inspection_sample_sections(
    inspection_records: pd.DataFrame,
    start_time: object | None = None,
    end_time: object | None = None,
    include_inspector_memory: bool = False,
    max_hours: int = 144,
    interval_hours: int = 12,
    rows_per_section: int = 10,
) -> dict[str, object]:
    effective_start, effective_end = resolve_inspection_sample_time_window(
        inspection_records,
        start_time=start_time,
        end_time=end_time,
    )
    filtered_records = filter_inspection_records_by_time_range(
        inspection_records,
        start_time=effective_start,
        end_time=effective_end,
    )

    if effective_start is None or effective_end is None or effective_start > effective_end:
        return {
            "effective_start": effective_start,
            "effective_end": effective_end,
            "sections": [],
        }

    sections: list[dict[str, object]] = []
    max_offset_hours = min(max_hours, 144)

    for offset_hours in range(0, max_offset_hours + 1, interval_hours):
        anchor_timestamp = effective_start + pd.Timedelta(hours=offset_hours)
        if anchor_timestamp > effective_end:
            break

        anchor_records = filtered_records[filtered_records["Timestamp"] >= anchor_timestamp].head(rows_per_section)
        if not anchor_records.empty:
            sections.append(
                {
                    "anchor_hours": offset_hours,
                    "anchor_timestamp": anchor_timestamp,
                    "status": "rows",
                    "message": None,
                    "dataframe": format_inspection_sample_dataframe(
                        anchor_records.reset_index(drop=True),
                        include_inspector_memory=include_inspector_memory,
                    ),
                }
            )
            continue

        if filtered_records.empty:
            message = "데이터가 존재하지 않습니다."
        else:
            last_before_anchor = filtered_records[filtered_records["Timestamp"] < anchor_timestamp]
            if last_before_anchor.empty:
                message = "데이터가 존재하지 않습니다."
            else:
                last_timestamp = pd.Timestamp(last_before_anchor.iloc[-1]["Timestamp"])
                elapsed = _format_elapsed_time_korean(anchor_timestamp - last_timestamp)
                message = (
                    f"마지막 데이터는 {last_timestamp.strftime('%Y-%m-%d %H:%M:%S')}이며 "
                    f"기준점보다 {elapsed} 이전 데이터가 최종 데이터입니다."
                )

        sections.append(
            {
                "anchor_hours": offset_hours,
                "anchor_timestamp": anchor_timestamp,
                "status": "message",
                "message": message,
                "dataframe": pd.DataFrame(),
            }
        )

    return {
        "effective_start": effective_start,
        "effective_end": effective_end,
        "sections": sections,
    }


def summarize_inspector_log_data(df: pd.DataFrame) -> dict[str, object]:
    empty_summary = {
        "rows": 0,
        "insp_rows": 0,
        "memory_rows": 0,
        "inspection_rows": 0,
        "time_range": None,
        "model_names": [],
        "source_types": [],
        "active_model_name": None,
        "max_frame_sec": None,
        "max_total_sec": None,
        "max_working_set_gb": None,
    }

    if df is None or df.empty:
        return empty_summary

    insp_rows = df["Inspector_Frame_Sec"].notna()
    memory_rows = df["Inspector_WorkingSet_GB"].notna()
    inspection_rows = build_inspection_records(df)
    model_names = _ordered_unique_non_empty(df.get("Inspector_Model_Name", []))
    source_types = _ordered_unique_non_empty(df.get("Inspector_Source_Type", []))

    return {
        "rows": int(len(df)),
        "insp_rows": int(insp_rows.sum()),
        "memory_rows": int(memory_rows.sum()),
        "inspection_rows": int(len(inspection_rows)),
        "time_range": (df["Timestamp"].min(), df["Timestamp"].max()),
        "model_names": model_names,
        "source_types": source_types,
        "active_model_name": model_names[-1] if model_names else None,
        "max_frame_sec": float(df.loc[insp_rows, "Inspector_Frame_Sec"].max()) if insp_rows.any() else None,
        "max_total_sec": float(df.loc[insp_rows, "Inspector_Total_Sec"].max()) if insp_rows.any() else None,
        "max_working_set_gb": float(df.loc[memory_rows, "Inspector_WorkingSet_GB"].max()) if memory_rows.any() else None,
    }


def summarize_inspection_records(df: pd.DataFrame) -> dict[str, object]:
    empty_summary = {
        "rows": 0,
        "model_names": [],
        "source_types": [],
        "primary_model_name": None,
        "no_range": None,
        "system_memory_matches": 0,
    }

    if df is None or df.empty:
        return empty_summary

    model_names = _ordered_unique_non_empty(df.get("Inspector_Model_Name", []))
    source_types = _ordered_unique_non_empty(df.get("Inspector_Source_Type", []))
    return {
        "rows": int(len(df)),
        "model_names": model_names,
        "source_types": source_types,
        "primary_model_name": model_names[-1] if model_names else None,
        "no_range": (
            int(pd.to_numeric(df["Inspection_No"], errors="coerce").min()),
            int(pd.to_numeric(df["Inspection_No"], errors="coerce").max()),
        ),
        "system_memory_matches": int(df["System_Memory_Used_GB"].notna().sum()) if "System_Memory_Used_GB" in df.columns else 0,
    }
