import json
import os
import platform
import sys
import tempfile
import traceback
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from collectors.cpu_temperature import (
    CpuTemperatureProbe,
    _normalize_json_records,
)
from collectors.cpu_temperature_worker import capture_and_write_state, load_state_payload
from collectors.dell_command_monitor import ensure_dcm_ready, get_system_identity, resolve_dcm_package
from collectors.libre_hardware_monitor import (
    LIBRE_HARDWARE_MONITOR_CORE_MAX_PROVIDER,
    ensure_lhm_bundle_dir,
    find_local_lhm_bundle_dir,
    read_cpu_core_max_temperature_sample,
    read_lhm_bundle_manifest,
)


RECORD_SUMMARY_FIELDS = (
    "ElementName",
    "Name",
    "InstanceName",
    "Identifier",
    "Parent",
    "DeviceID",
    "SensorType",
    "Value",
    "CurrentReading",
    "CurrentTemperature",
    "Temperature",
    "BaseUnits",
    "UnitModifier",
)
MAX_RECORD_PREVIEW = 8


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _sanitize_for_json(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _sanitize_for_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_for_json(item) for item in value]
    return str(value)


def _summarize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summarized = []
    for record in records[:MAX_RECORD_PREVIEW]:
        summary = {}
        for field in RECORD_SUMMARY_FIELDS:
            value = record.get(field)
            if value in (None, ""):
                continue
            summary[field] = _sanitize_for_json(value)
        summarized.append(summary)
    return summarized


def _inspect_provider(probe: CpuTemperatureProbe, provider_name: str, script: str, selector) -> dict[str, Any]:
    try:
        payload = probe._run_powershell(script)
        records = _normalize_json_records(payload)
        selected = selector(records) if records else None
        return {
            "provider_name": provider_name,
            "record_count": len(records),
            "selected_value_c": round(selected.value_c, 1) if selected is not None else None,
            "selected_detail": selected.detail if selected is not None else None,
            "record_preview": _summarize_records(records),
        }
    except Exception as exc:
        return {
            "provider_name": provider_name,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }


def collect_cpu_temperature_diagnostics() -> dict[str, Any]:
    manufacturer, model = get_system_identity()
    is_target_dell_system = resolve_dcm_package(manufacturer, model) is not None
    dcm_result = ensure_dcm_ready(auto_install=False)
    probe = CpuTemperatureProbe(retry_interval_sec=0.0, system_identity=(manufacturer, model))

    diagnostics: dict[str, Any] = {
        "generated_at": _now_iso(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python_executable": sys.executable,
            "python_version": sys.version,
            "frozen": bool(getattr(sys, "frozen", False)),
        },
        "system_identity": {
            "manufacturer": manufacturer,
            "model": model,
            "is_target_dell_system": is_target_dell_system,
        },
        "dcm_bootstrap": _sanitize_for_json(asdict(dcm_result)),
        "probe": {
            "enable_dell_command_monitor": probe.enable_dell_command_monitor,
            "provider_order": [provider_name for provider_name, *_ in probe._providers],
            "state_path": str(probe._state_path),
        },
    }

    state_before = load_state_payload(probe._state_path)
    diagnostics["worker_state_before"] = _sanitize_for_json(state_before)

    if not is_target_dell_system:
        lhm_section: dict[str, Any] = {
            "provider_name": LIBRE_HARDWARE_MONITOR_CORE_MAX_PROVIDER,
            "local_bundle_dir": _sanitize_for_json(find_local_lhm_bundle_dir()),
            "manifest": _sanitize_for_json(read_lhm_bundle_manifest()),
        }
        try:
            bundle_dir = ensure_lhm_bundle_dir()
            lhm_section["bundle_dir"] = str(bundle_dir)
            lhm_section["bundle_source"] = (
                "local-bundled" if find_local_lhm_bundle_dir() is not None and bundle_dir == find_local_lhm_bundle_dir() else "cache-or-download"
            )
        except Exception as exc:
            lhm_section["bundle_dir_error"] = str(exc)
            lhm_section["bundle_dir_traceback"] = traceback.format_exc()

        try:
            sample = read_cpu_core_max_temperature_sample()
            lhm_section["direct_sample"] = _sanitize_for_json(asdict(sample) if sample is not None else None)
        except Exception as exc:
            lhm_section["direct_sample_error"] = str(exc)
            lhm_section["direct_sample_traceback"] = traceback.format_exc()

        try:
            capture_ok = capture_and_write_state(probe._state_path)
            lhm_section["capture_and_write_state_ok"] = bool(capture_ok)
        except Exception as exc:
            lhm_section["capture_and_write_state_ok"] = False
            lhm_section["capture_error"] = str(exc)
            lhm_section["capture_traceback"] = traceback.format_exc()

        diagnostics["lhm_worker"] = lhm_section
        diagnostics["worker_state_after"] = _sanitize_for_json(load_state_payload(probe._state_path))

    try:
        value_c = probe.read_celsius(force_refresh=True)
        diagnostics["force_refresh_probe"] = {
            "value_c": value_c,
            "source_name": probe.source_name,
            "source_detail": probe.source_detail,
        }
    except Exception as exc:
        diagnostics["force_refresh_probe"] = {
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }

    diagnostics["provider_diagnostics"] = [
        _inspect_provider(probe, provider_name, script, selector)
        for provider_name, script, selector in probe._providers
    ]

    probe.close()
    return diagnostics


def _resolve_output_dir(output_dir: Optional[Path | str]) -> Path:
    if output_dir is not None:
        candidate = Path(output_dir)
    else:
        candidate = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "PC-monitor-Tools" / "diagnostics"

    try:
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    except OSError:
        fallback_dir = Path(tempfile.gettempdir()) / "PC-monitor-Tools" / "diagnostics"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir


def write_cpu_temperature_diagnostic_log(output_dir: Optional[Path | str] = None) -> tuple[dict[str, Any], Path, Path]:
    diagnostics = collect_cpu_temperature_diagnostics()
    resolved_output_dir = _resolve_output_dir(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = resolved_output_dir / f"cpu_temp_diagnostic_{timestamp}.log"
    latest_path = resolved_output_dir / "cpu_temp_diagnostic_latest.log"
    contents = json.dumps(_sanitize_for_json(diagnostics), ensure_ascii=False, indent=2)
    log_path.write_text(contents, encoding="utf-8")
    latest_path.write_text(contents, encoding="utf-8")
    return diagnostics, log_path, latest_path
