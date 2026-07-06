from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from typing import Iterable

import pandas as pd


SPI_SOURCE_TYPE = "SPI"
SPI_MEMORY_KEY = "SPI"

SPI_SEPARATOR = "++++++++++++++++++++++++++++++++++++++++++++++++++"
SPI_START_PATTERN = re.compile(r"검사\s*시작\s*\[\s*일련\s*번호\s*:\s*(?P<serial>[^\]\s]+)\s*\]")
SPI_END_PATTERN = re.compile(r"검사\s*종료\s*\[\s*경과\s*시간\s*:\s*(?P<elapsed>[\d.]+)\s*초\s*\]")
SPI_FRAME_PATTERN = re.compile(
    r"프레임당\s*검사\s*시간\s*:\s*(?P<frame_sec>[\d.]+)\s*초/프레임\s*"
    r"\(\s*(?P<frame_total_sec>[\d.]+)\s*초\s*/\s*(?P<frame_count>\d+)\s*프레임\s*\)"
)
SPI_TIMESTAMP_PATTERN = re.compile(
    r"(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<period>오전|오후)\s+"
    r"(?P<hour>\d{1,2}):(?P<minute>\d{2}):(?P<second>\d{2})"
)
PROCESS_RESOURCE_PATTERN = re.compile(
    r"\[(?P<stamp>\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\]"
    r"\[\[WorkingSet\]=(?P<working_set>\d+)\s*KB,\s*"
    r"\[Private\]=(?P<private>\d+)\s*KB,\s*"
    r"\[Pagefile\]=(?P<pagefile>\d+)\s*KB,",
    re.IGNORECASE,
)


@dataclass
class SpiInspectionBlock:
    start_timestamp: pd.Timestamp | None = None
    end_timestamp: pd.Timestamp | None = None
    serial_number: str | None = None
    elapsed_sec: float | None = None
    frame_sec: float | None = None
    frame_total_sec: float | None = None
    frame_count: int | None = None
    has_content: bool = False

    def reset(self) -> None:
        self.start_timestamp = None
        self.end_timestamp = None
        self.serial_number = None
        self.elapsed_sec = None
        self.frame_sec = None
        self.frame_total_sec = None
        self.frame_count = None
        self.has_content = False

    def to_event_row(self, source_file: str) -> dict[str, object] | None:
        if self.end_timestamp is None:
            return None
        if self.elapsed_sec is None and self.frame_total_sec is None:
            return None

        total_sec = self.elapsed_sec if self.elapsed_sec is not None else self.frame_total_sec
        return {
            "Timestamp": self.end_timestamp,
            "SourceFile": source_file,
            "Inspector_Event_Type": "insp_time",
            "Inspector_Source_Type": SPI_SOURCE_TYPE,
            "Inspector_Memory_Key": SPI_MEMORY_KEY,
            "Inspector_Model_Name": SPI_SOURCE_TYPE,
            "Inspector_Frame_Sec": self.frame_sec if self.frame_sec is not None else pd.NA,
            "Inspector_Total_Sec": total_sec,
            "Inspector_Total_Frames": self.frame_count if self.frame_count is not None else pd.NA,
            "Inspector_WorkingSet_KB": pd.NA,
            "Inspector_WorkingSet_MB": pd.NA,
            "Inspector_WorkingSet_GB": pd.NA,
        }


def _parse_spi_timestamp(value: object) -> pd.Timestamp | None:
    match = SPI_TIMESTAMP_PATTERN.search(str(value or "").strip())
    if not match:
        return None

    hour = int(match.group("hour"))
    if match.group("period") == "오후" and hour != 12:
        hour += 12
    elif match.group("period") == "오전" and hour == 12:
        hour = 0

    return pd.Timestamp(
        year=int(match.group("date")[0:4]),
        month=int(match.group("date")[5:7]),
        day=int(match.group("date")[8:10]),
        hour=hour,
        minute=int(match.group("minute")),
        second=int(match.group("second")),
    )


def _build_working_set_row(source_file: str, timestamp: pd.Timestamp, working_set_kb: float) -> dict[str, object]:
    return {
        "Timestamp": timestamp,
        "SourceFile": source_file,
        "Inspector_Event_Type": "working_set",
        "Inspector_Source_Type": SPI_SOURCE_TYPE,
        "Inspector_Memory_Key": SPI_MEMORY_KEY,
        "Inspector_Model_Name": pd.NA,
        "Inspector_Frame_Sec": pd.NA,
        "Inspector_Total_Sec": pd.NA,
        "Inspector_Total_Frames": pd.NA,
        "Inspector_WorkingSet_KB": working_set_kb,
        "Inspector_WorkingSet_MB": working_set_kb / 1024.0,
        "Inspector_WorkingSet_GB": working_set_kb / (1024.0 * 1024.0),
    }


def parse_process_resource_lines(lines: Iterable[str], source_file: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for line in lines:
        match = PROCESS_RESOURCE_PATTERN.search(line)
        if not match:
            continue

        timestamp = pd.to_datetime(match.group("stamp"), format="%Y/%m/%d %H:%M:%S", errors="coerce")
        if pd.isna(timestamp):
            continue
        rows.append(_build_working_set_row(source_file, pd.Timestamp(timestamp), float(match.group("working_set"))))

    return rows


def _read_spi_csv_rows(lines: Iterable[str]) -> list[dict[str, str]]:
    text = "\n".join(lines)
    if "Time" not in text or "Description" not in text:
        return []
    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames is None:
        return []

    normalized_fields = [field.strip() for field in reader.fieldnames]
    if not {"Time", "Description"}.issubset(normalized_fields):
        return []

    rows = []
    for raw_row in reader:
        normalized_row = {str(key).strip(): value for key, value in raw_row.items() if key is not None}
        rows.append(normalized_row)
    return rows


def parse_spi_csv_lines(lines: Iterable[str], source_file: str) -> list[dict[str, object]]:
    csv_rows = _read_spi_csv_rows(lines)
    if not csv_rows:
        return []

    events: list[dict[str, object]] = []
    block = SpiInspectionBlock()

    def finalize_block() -> None:
        event_row = block.to_event_row(source_file)
        if event_row is not None:
            events.append(event_row)
        block.reset()

    for csv_row in csv_rows:
        timestamp = _parse_spi_timestamp(csv_row.get("Time"))
        description = str(csv_row.get("Description") or "").strip()
        if not description:
            continue

        if SPI_SEPARATOR in description:
            finalize_block()
            continue

        if timestamp is not None:
            block.has_content = True

        start_match = SPI_START_PATTERN.search(description)
        if start_match:
            if block.has_content and (block.end_timestamp is not None or block.frame_sec is not None):
                finalize_block()
            block.start_timestamp = timestamp
            block.serial_number = start_match.group("serial").strip()
            block.has_content = True
            continue

        end_match = SPI_END_PATTERN.search(description)
        if end_match:
            block.end_timestamp = timestamp
            block.elapsed_sec = float(end_match.group("elapsed"))
            block.has_content = True
            continue

        frame_match = SPI_FRAME_PATTERN.search(description)
        if frame_match:
            block.frame_sec = float(frame_match.group("frame_sec"))
            block.frame_total_sec = float(frame_match.group("frame_total_sec"))
            block.frame_count = int(frame_match.group("frame_count"))
            block.has_content = True

    finalize_block()
    return events


def parse_spi_rows(lines: Iterable[str], source_file: str) -> list[dict[str, object]]:
    line_list = list(lines)
    return [
        *parse_spi_csv_lines(line_list, source_file),
        *parse_process_resource_lines(line_list, source_file),
    ]
