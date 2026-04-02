import json
import subprocess
import time
from typing import Any, Iterable, Optional


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

CPU_SENSOR_KEYWORDS = (
    "cpu",
    "package",
    "tdie",
    "tctl",
    "ccd",
    "core",
)

LIBRE_HARDWARE_MONITOR_SCRIPT = """
$records = Get-CimInstance -Namespace root\\LibreHardwareMonitor -ClassName Sensor -ErrorAction Stop |
    Where-Object { $_.SensorType -eq 'Temperature' } |
    Select-Object Name, SensorType, Value, Identifier, Parent
if ($null -ne $records) {
    $records | ConvertTo-Json -Compress
}
"""

OPEN_HARDWARE_MONITOR_SCRIPT = """
$records = Get-CimInstance -Namespace root\\OpenHardwareMonitor -ClassName Sensor -ErrorAction Stop |
    Where-Object { $_.SensorType -eq 'Temperature' } |
    Select-Object Name, SensorType, Value, Identifier, Parent
if ($null -ne $records) {
    $records | ConvertTo-Json -Compress
}
"""

MS_ACPI_THERMAL_ZONE_SCRIPT = """
$records = Get-CimInstance -Namespace root\\wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction Stop |
    Select-Object CurrentTemperature, InstanceName
if ($null -ne $records) {
    $records | ConvertTo-Json -Compress
}
"""


def _normalize_json_records(payload: str) -> list[dict[str, Any]]:
    payload = (payload or "").strip()
    if not payload:
        return []

    data = json.loads(payload)
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _matches_cpu_sensor(record: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(record.get(field, ""))
        for field in ("Name", "Identifier", "Parent", "InstanceName")
    ).lower()
    return any(keyword in haystack for keyword in CPU_SENSOR_KEYWORDS)


def _coerce_float(value: Any) -> Optional[float]:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def _select_max_sensor_temperature(records: Iterable[dict[str, Any]]) -> Optional[float]:
    cpu_values = []

    for record in records:
        value = _coerce_float(record.get("Value"))
        if value is None:
            continue
        if _matches_cpu_sensor(record):
            cpu_values.append(value)

    if cpu_values:
        return max(cpu_values)
    return None


def _select_max_thermal_zone_temperature(records: Iterable[dict[str, Any]]) -> Optional[float]:
    values_c = []

    for record in records:
        raw_value = _coerce_float(record.get("CurrentTemperature"))
        if raw_value is None or raw_value <= 0:
            continue
        values_c.append((raw_value / 10.0) - 273.15)

    if not values_c:
        return None
    return max(values_c)


class CpuTemperatureProbe:
    _PROVIDERS = (
        ("LibreHardwareMonitor", LIBRE_HARDWARE_MONITOR_SCRIPT, _select_max_sensor_temperature),
        ("OpenHardwareMonitor", OPEN_HARDWARE_MONITOR_SCRIPT, _select_max_sensor_temperature),
        ("MSAcpiThermalZone", MS_ACPI_THERMAL_ZONE_SCRIPT, _select_max_thermal_zone_temperature),
    )

    def __init__(self, retry_interval_sec: float = 30.0, command_timeout_sec: float = 1.5):
        self.retry_interval_sec = retry_interval_sec
        self.command_timeout_sec = command_timeout_sec
        self.source_name: Optional[str] = None
        self._last_probe_time = 0.0

    def _run_powershell(self, script: str) -> str:
        try:
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    script,
                ],
                capture_output=True,
                text=True,
                timeout=self.command_timeout_sec,
                creationflags=CREATE_NO_WINDOW,
                check=False,
            )
        except (FileNotFoundError, subprocess.SubprocessError, OSError):
            return ""

        if completed.returncode != 0:
            return ""
        return completed.stdout.strip()

    def _query_provider(self, provider_name: str, script: str, selector) -> Optional[float]:
        payload = self._run_powershell(script)
        records = _normalize_json_records(payload)
        if not records:
            return None

        selected = selector(records)
        if selected is None:
            return None

        self.source_name = provider_name
        return round(selected, 1)

    def read_celsius(self, force_refresh: bool = False) -> Optional[float]:
        now = time.monotonic()
        if not force_refresh and self.source_name is None and (now - self._last_probe_time) < self.retry_interval_sec:
            return None

        self._last_probe_time = now

        if self.source_name is not None:
            for provider_name, script, selector in self._PROVIDERS:
                if provider_name != self.source_name:
                    continue
                value = self._query_provider(provider_name, script, selector)
                if value is not None:
                    return value
                self.source_name = None
                break

        for provider_name, script, selector in self._PROVIDERS:
            value = self._query_provider(provider_name, script, selector)
            if value is not None:
                return value

        return None
