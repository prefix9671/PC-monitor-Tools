import json
import subprocess
import time
from typing import Any, Iterable, Optional

from collectors.dell_command_monitor import should_use_dell_command_monitor_provider


CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

CPU_PACKAGE_SENSOR_KEYWORDS = (
    "cpu package",
    "package id",
    "processor package",
    "cpu temp",
    "cpu temperature",
    "tdie",
    "tctl",
)

CPU_SENSOR_KEYWORDS = (
    "cpu",
    "processor",
    "package",
    "tdie",
    "tctl",
    "ccd",
    "core",
)

SENSOR_TEXT_FIELDS = (
    "Name",
    "Identifier",
    "Parent",
    "InstanceName",
    "ElementName",
    "DeviceID",
)

DELL_COMMAND_MONITOR_SCRIPT = """
$records = Get-CimInstance -Namespace root\\dcim\\sysman -ClassName DCIM_NumericSensor -ErrorAction Stop |
    Where-Object {
        ($_.SensorType -eq 2 -or "$($_.SensorType)" -eq '2' -or "$($_.SensorType)" -match 'Temperature') -and
        ($_.ElementName -like '*Temperature*' -or $_.BaseUnits -eq 2 -or "$($_.BaseUnits)" -match 'Celsius')
    } |
    Select-Object ElementName, DeviceID, CurrentReading, UnitModifier, BaseUnits, SensorType
if ($null -ne $records) {
    $records | ConvertTo-Json -Compress
}
"""

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


def _record_text(record: dict[str, Any]) -> str:
    return " ".join(str(record.get(field, "")) for field in SENSOR_TEXT_FIELDS).lower()


def _matches_keywords(record: dict[str, Any], keywords: tuple[str, ...]) -> bool:
    haystack = _record_text(record)
    return any(keyword in haystack for keyword in keywords)


def _matches_cpu_package_sensor(record: dict[str, Any]) -> bool:
    return _matches_keywords(record, CPU_PACKAGE_SENSOR_KEYWORDS)


def _matches_cpu_sensor(record: dict[str, Any]) -> bool:
    return _matches_keywords(record, CPU_SENSOR_KEYWORDS)


def _coerce_float(value: Any) -> Optional[float]:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def _is_plausible_temperature_celsius(value: Optional[float]) -> bool:
    return value is not None and 0.0 <= value <= 150.0


def _convert_base_unit_to_celsius(value: float, base_units: str) -> Optional[float]:
    normalized = base_units.strip().lower()
    if not normalized or normalized == "2" or "celsius" in normalized or "deg c" in normalized:
        return value
    if normalized == "3" or "fahrenheit" in normalized or "deg f" in normalized:
        return (value - 32.0) * (5.0 / 9.0)
    if normalized == "4" or "kelvin" in normalized:
        return value - 273.15
    return None


def _select_max_sensor_temperature(records: Iterable[dict[str, Any]]) -> Optional[float]:
    package_values = []
    cpu_values = []

    for record in records:
        value = _coerce_float(record.get("Value"))
        if value is None:
            continue
        if _matches_cpu_package_sensor(record):
            package_values.append(value)
            continue
        if _matches_cpu_sensor(record):
            cpu_values.append(value)

    if package_values:
        return max(package_values)
    if cpu_values:
        return max(cpu_values)
    return None


def _convert_numeric_sensor_to_celsius(record: dict[str, Any]) -> Optional[float]:
    raw_value = _coerce_float(record.get("CurrentReading"))
    if raw_value is None:
        return None

    unit_modifier = _coerce_float(record.get("UnitModifier"))
    scaled_value = raw_value * (10 ** int(unit_modifier or 0))
    base_units = str(record.get("BaseUnits", "")).strip().lower()

    raw_celsius = _convert_base_unit_to_celsius(raw_value, base_units)
    scaled_celsius = _convert_base_unit_to_celsius(scaled_value, base_units)

    raw_plausible = _is_plausible_temperature_celsius(raw_celsius)
    scaled_plausible = _is_plausible_temperature_celsius(scaled_celsius)

    # Dell temperature sensors on Precision workstations can report UnitModifier=-1
    # while threshold examples and runtime behavior still use whole-degree readings.
    # Prefer the direct reading when it looks like a real temperature, and only fall
    # back to the scaled interpretation when the raw value is implausible.
    if raw_plausible and not scaled_plausible:
        return raw_celsius
    if scaled_plausible and not raw_plausible:
        return scaled_celsius
    if raw_plausible:
        return raw_celsius
    if scaled_plausible:
        return scaled_celsius
    return None


def _select_dell_command_monitor_temperature(records: Iterable[dict[str, Any]]) -> Optional[float]:
    package_values = []
    cpu_values = []

    for record in records:
        value = _convert_numeric_sensor_to_celsius(record)
        if value is None:
            continue
        if _matches_cpu_package_sensor(record):
            package_values.append(value)
            continue
        if _matches_cpu_sensor(record):
            cpu_values.append(value)

    if package_values:
        return max(package_values)
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
    _DCM_PROVIDER = ("DellCommandMonitor", DELL_COMMAND_MONITOR_SCRIPT, _select_dell_command_monitor_temperature)
    _FALLBACK_PROVIDERS = (
        ("LibreHardwareMonitor", LIBRE_HARDWARE_MONITOR_SCRIPT, _select_max_sensor_temperature),
        ("OpenHardwareMonitor", OPEN_HARDWARE_MONITOR_SCRIPT, _select_max_sensor_temperature),
        ("MSAcpiThermalZone", MS_ACPI_THERMAL_ZONE_SCRIPT, _select_max_thermal_zone_temperature),
    )

    def __init__(
        self,
        retry_interval_sec: float = 30.0,
        command_timeout_sec: float = 1.5,
        enable_dell_command_monitor: Optional[bool] = None,
    ):
        self.retry_interval_sec = retry_interval_sec
        self.command_timeout_sec = command_timeout_sec
        self.source_name: Optional[str] = None
        self._last_probe_time = 0.0
        if enable_dell_command_monitor is None:
            self.enable_dell_command_monitor = should_use_dell_command_monitor_provider(timeout_sec=command_timeout_sec)
        else:
            self.enable_dell_command_monitor = enable_dell_command_monitor

    @property
    def _providers(self):
        if self.enable_dell_command_monitor:
            return (self._DCM_PROVIDER, *self._FALLBACK_PROVIDERS)
        return self._FALLBACK_PROVIDERS

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
            for provider_name, script, selector in self._providers:
                if provider_name != self.source_name:
                    continue
                value = self._query_provider(provider_name, script, selector)
                if value is not None:
                    return value
                self.source_name = None
                break

        for provider_name, script, selector in self._providers:
            value = self._query_provider(provider_name, script, selector)
            if value is not None:
                return value

        return None
