from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import pandas as pd

INSPECTOR_PROCESS_LABEL = "Inspector APP (log)"
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

INSPECTOR_COLUMNS = [
    "Timestamp",
    "SourceFile",
    "Inspector_Event_Type",
    "Inspector_Frame_Sec",
    "Inspector_Total_Sec",
    "Inspector_Total_Frames",
    "Inspector_WorkingSet_KB",
    "Inspector_WorkingSet_MB",
    "Inspector_WorkingSet_GB",
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
    insp_match = INSPTIME_PATTERN.search(line)
    if insp_match:
        return {
            "Timestamp": pd.to_datetime(insp_match.group("stamp"), format="%Y%m%d_%H%M%S", errors="coerce"),
            "SourceFile": source_file,
            "Inspector_Event_Type": "insp_time",
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
            if "|InspTime|" not in line and "Working Set Memory Size" not in line:
                continue
            parsed = _parse_line(line, log_path.name)
            if parsed is not None:
                rows.append(parsed)

    return _rows_to_dataframe(rows)


def load_inspector_log_data_from_uploads(uploaded_files: Iterable[tuple[str, bytes]] | None) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for file_name, raw_bytes in uploaded_files or []:
        for line in _decode_text_lines(raw_bytes):
            if "|InspTime|" not in line and "Working Set Memory Size" not in line:
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
    return df.dropna(subset=["Timestamp"]).sort_values("Timestamp").reset_index(drop=True)


def summarize_inspector_log_data(df: pd.DataFrame) -> dict[str, object]:
    empty_summary = {
        "rows": 0,
        "insp_rows": 0,
        "memory_rows": 0,
        "time_range": None,
        "max_frame_sec": None,
        "max_total_sec": None,
        "max_working_set_gb": None,
    }

    if df is None or df.empty:
        return empty_summary

    insp_rows = df["Inspector_Frame_Sec"].notna()
    memory_rows = df["Inspector_WorkingSet_GB"].notna()

    return {
        "rows": int(len(df)),
        "insp_rows": int(insp_rows.sum()),
        "memory_rows": int(memory_rows.sum()),
        "time_range": (df["Timestamp"].min(), df["Timestamp"].max()),
        "max_frame_sec": float(df.loc[insp_rows, "Inspector_Frame_Sec"].max()) if insp_rows.any() else None,
        "max_total_sec": float(df.loc[insp_rows, "Inspector_Total_Sec"].max()) if insp_rows.any() else None,
        "max_working_set_gb": float(df.loc[memory_rows, "Inspector_WorkingSet_GB"].max()) if memory_rows.any() else None,
    }
