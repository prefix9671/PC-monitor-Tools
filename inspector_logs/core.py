from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd

INSPECTOR_PROCESS_LABEL = "인스펙터 앱 (로그)"
SUPPORTED_LOG_SUFFIXES = (".log", ".txt")

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


def _read_text_lines(path: Path) -> list[str]:
    raw_bytes = path.read_bytes()
    return _decode_text_lines(raw_bytes)


def _decode_text_lines(raw_bytes: bytes) -> list[str]:
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return raw_bytes.decode(encoding).splitlines()
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("latin-1", errors="ignore").splitlines()


def _parse_line(line: str, source_file: str) -> dict[str, object] | None:
    model_match = MODEL_OPEN_PATTERN.search(line)
    if model_match:
        return {
            "Timestamp": pd.to_datetime(model_match.group("stamp"), format="%Y%m%d_%H%M%S", errors="coerce"),
            "SourceFile": source_file,
            "Inspector_Event_Type": "model_open",
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
            "Inspector_Model_Name": pd.NA,
            "Inspector_Frame_Sec": pd.NA,
            "Inspector_Total_Sec": pd.NA,
            "Inspector_Total_Frames": pd.NA,
            "Inspector_WorkingSet_KB": working_set_kb,
            "Inspector_WorkingSet_MB": working_set_kb / 1024.0,
            "Inspector_WorkingSet_GB": working_set_kb / (1024.0 * 1024.0),
        }

    return None


def load_inspector_log_data(path_input: str | Iterable[str] | None) -> pd.DataFrame:
    resolved_paths = resolve_inspector_log_paths(path_input)
    rows: list[dict[str, object]] = []

    for log_path in resolved_paths:
        for line in _read_text_lines(log_path):
            normalized_line = line.lower()
            if "|insptime|" not in normalized_line and "working set memory size" not in normalized_line and "model open" not in normalized_line:
                continue
            parsed = _parse_line(line, log_path.name)
            if parsed is not None:
                rows.append(parsed)

    return _rows_to_dataframe(rows)


def load_inspector_log_data_from_uploads(uploaded_files: Iterable[tuple[str, bytes]] | None) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for file_name, raw_bytes in uploaded_files or []:
        for line in _decode_text_lines(raw_bytes):
            normalized_line = line.lower()
            if "|insptime|" not in normalized_line and "working set memory size" not in normalized_line and "model open" not in normalized_line:
                continue
            parsed = _parse_line(line, file_name)
            if parsed is not None:
                rows.append(parsed)

    return _rows_to_dataframe(rows)


def _rows_to_dataframe(rows: list[dict[str, object]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=INSPECTOR_COLUMNS)

    df = pd.DataFrame(rows, columns=INSPECTOR_COLUMNS)
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
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
    events["Timestamp"] = pd.to_datetime(events["Timestamp"], errors="coerce")
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
            model_rows[["Timestamp", "SourceFile", "Inspector_Model_Name"]],
            on="Timestamp",
            by="SourceFile",
            direction="backward",
            allow_exact_matches=True,
        )
    else:
        insp_rows["Inspector_Model_Name"] = pd.NA

    memory_rows = events.loc[
        events["Inspector_Event_Type"] == "working_set",
        [
            "Timestamp",
            "SourceFile",
            "Inspector_WorkingSet_KB",
            "Inspector_WorkingSet_MB",
            "Inspector_WorkingSet_GB",
            "_EventOrder",
        ],
    ].copy()

    if not memory_rows.empty:
        memory_rows = memory_rows.sort_values(["SourceFile", "Timestamp", "_EventOrder"], kind="mergesort")
        insp_rows = pd.merge_asof(
            insp_rows,
            memory_rows[
                [
                    "Timestamp",
                    "SourceFile",
                    "Inspector_WorkingSet_KB",
                    "Inspector_WorkingSet_MB",
                    "Inspector_WorkingSet_GB",
                ]
            ],
            on="Timestamp",
            by="SourceFile",
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
        system_memory["Timestamp"] = pd.to_datetime(system_memory["Timestamp"], errors="coerce")
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


def _format_inspection_dataframe(
    inspection_records: pd.DataFrame,
    selected_columns: list[str],
    renamed_columns: dict[str, str],
) -> pd.DataFrame:
    if inspection_records is None or inspection_records.empty:
        return pd.DataFrame(columns=list(renamed_columns.values()))

    export_df = inspection_records[selected_columns].copy()
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


def summarize_inspector_log_data(df: pd.DataFrame) -> dict[str, object]:
    empty_summary = {
        "rows": 0,
        "insp_rows": 0,
        "memory_rows": 0,
        "inspection_rows": 0,
        "time_range": None,
        "model_names": [],
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

    return {
        "rows": int(len(df)),
        "insp_rows": int(insp_rows.sum()),
        "memory_rows": int(memory_rows.sum()),
        "inspection_rows": int(len(inspection_rows)),
        "time_range": (df["Timestamp"].min(), df["Timestamp"].max()),
        "model_names": model_names,
        "active_model_name": model_names[-1] if model_names else None,
        "max_frame_sec": float(df.loc[insp_rows, "Inspector_Frame_Sec"].max()) if insp_rows.any() else None,
        "max_total_sec": float(df.loc[insp_rows, "Inspector_Total_Sec"].max()) if insp_rows.any() else None,
        "max_working_set_gb": float(df.loc[memory_rows, "Inspector_WorkingSet_GB"].max()) if memory_rows.any() else None,
    }


def summarize_inspection_records(df: pd.DataFrame) -> dict[str, object]:
    empty_summary = {
        "rows": 0,
        "model_names": [],
        "primary_model_name": None,
        "no_range": None,
        "system_memory_matches": 0,
    }

    if df is None or df.empty:
        return empty_summary

    model_names = _ordered_unique_non_empty(df.get("Inspector_Model_Name", []))
    return {
        "rows": int(len(df)),
        "model_names": model_names,
        "primary_model_name": model_names[-1] if model_names else None,
        "no_range": (
            int(pd.to_numeric(df["Inspection_No"], errors="coerce").min()),
            int(pd.to_numeric(df["Inspection_No"], errors="coerce").max()),
        ),
        "system_memory_matches": int(df["System_Memory_Used_GB"].notna().sum()) if "System_Memory_Used_GB" in df.columns else 0,
    }
