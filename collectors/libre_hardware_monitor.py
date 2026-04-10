import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


LIBRE_HARDWARE_MONITOR_CORE_MAX_PROVIDER = "LibreHardwareMonitorCoreMax"
LHM_RELEASE_API_URL = "https://api.github.com/repos/LibreHardwareMonitor/LibreHardwareMonitor/releases/latest"
LHM_CACHE_DIR = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "PC-monitor-Tools" / "lhm-cache"
LHM_MANIFEST_PATH = LHM_CACHE_DIR / "bundle-manifest.json"
LHM_DLL_NAME = "LibreHardwareMonitorLib.dll"
LHM_BUNDLE_DIRNAME = "lhm-bundle"
LHM_BUNDLE_MANIFEST_NAME = "bundle-manifest.json"
LHM_VENDOR_BUNDLE_DIR = Path(".artifacts") / "vendor" / LHM_BUNDLE_DIRNAME
LHM_PREFERRED_ASSET_NAMES = (
    "LibreHardwareMonitor.zip",
    "LibreHardwareMonitor.NET.10.zip",
)

CPU_CORE_SENSOR_PATTERN = re.compile(r"(?:^|\b)(?:cpu\s+)?core\s*#?\s*(\d+)\b", re.IGNORECASE)
NON_CORE_SENSOR_KEYWORDS = (
    "core max",
    "core average",
    "distance to tjmax",
)

_PYTHONNET_INITIALIZED = False
_LHM_ASSEMBLY_LOADED = False


@dataclass(frozen=True)
class LhmReleaseAsset:
    version: str
    asset_name: str
    download_url: str
    sha256: Optional[str]
    html_url: str


@dataclass(frozen=True)
class LhmCpuCoreTemperatureSample:
    value_c: float
    detail: str
    sensor_name: str
    hardware_name: str


def _request_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PC-monitor-Tools",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _read_manifest() -> Optional[dict[str, str]]:
    if not LHM_MANIFEST_PATH.exists():
        return None
    try:
        return json.loads(LHM_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_manifest(asset: LhmReleaseAsset, bundle_dir: Path) -> None:
    payload = {
        "version": asset.version,
        "asset_name": asset.asset_name,
        "download_url": asset.download_url,
        "sha256": asset.sha256 or "",
        "html_url": asset.html_url,
        "bundle_dir": str(bundle_dir),
    }
    LHM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LHM_MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sanitize_bundle_name(version: str, asset_name: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", asset_name)
    return f"{version}-{safe_name[:-4] if safe_name.lower().endswith('.zip') else safe_name}"


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "PC-monitor-Tools"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        output.write(response.read())


def _select_release_asset(release_payload: dict[str, Any]) -> LhmReleaseAsset:
    assets = release_payload.get("assets") or []
    by_name = {str(asset.get("name", "")): asset for asset in assets if isinstance(asset, dict)}

    selected = None
    for preferred_name in LHM_PREFERRED_ASSET_NAMES:
        selected = by_name.get(preferred_name)
        if selected is not None:
            break

    if selected is None:
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name", ""))
            if "LibreHardwareMonitor" in name and name.lower().endswith(".zip"):
                selected = asset
                break

    if selected is None:
        raise RuntimeError("LibreHardwareMonitor latest release does not expose a usable zip asset.")

    digest = str(selected.get("digest", "")).strip()
    sha256_value = None
    if digest.lower().startswith("sha256:"):
        sha256_value = digest.split(":", 1)[1]

    return LhmReleaseAsset(
        version=str(release_payload.get("tag_name") or release_payload.get("name") or "latest"),
        asset_name=str(selected.get("name") or "LibreHardwareMonitor.zip"),
        download_url=str(selected.get("browser_download_url") or ""),
        sha256=sha256_value,
        html_url=str(release_payload.get("html_url") or ""),
    )


def _cached_bundle_dir_from_manifest() -> Optional[Path]:
    manifest = _read_manifest()
    if manifest is None:
        return None

    bundle_dir = Path(manifest.get("bundle_dir", "")).expanduser()
    if _is_valid_bundle_dir(bundle_dir):
        return bundle_dir
    return None


def _is_valid_bundle_dir(bundle_dir: Optional[Path]) -> bool:
    if bundle_dir is None:
        return False
    try:
        return bundle_dir.exists() and (bundle_dir / LHM_DLL_NAME).exists()
    except OSError:
        return False


def _local_bundle_dir_candidates() -> list[Path]:
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / LHM_BUNDLE_DIRNAME)

    executable_dir = Path(sys.executable).resolve().parent
    candidates.append(executable_dir / LHM_BUNDLE_DIRNAME)

    repo_root = Path(__file__).resolve().parents[1]
    candidates.append(repo_root / LHM_VENDOR_BUNDLE_DIR)
    return candidates


def find_local_lhm_bundle_dir() -> Optional[Path]:
    for candidate in _local_bundle_dir_candidates():
        if _is_valid_bundle_dir(candidate):
            return candidate
    return None


def ensure_lhm_bundle_dir() -> Path:
    local_bundle_dir = find_local_lhm_bundle_dir()
    if local_bundle_dir is not None:
        return local_bundle_dir

    cached_bundle_dir = _cached_bundle_dir_from_manifest()
    if cached_bundle_dir is not None:
        return cached_bundle_dir

    LHM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    release_payload = _request_json(LHM_RELEASE_API_URL)
    asset = _select_release_asset(release_payload)

    archive_path = LHM_CACHE_DIR / asset.asset_name
    bundle_dir = LHM_CACHE_DIR / _sanitize_bundle_name(asset.version, asset.asset_name)

    if not archive_path.exists():
        _download_file(asset.download_url, archive_path)

    if asset.sha256:
        actual_hash = _sha256_file(archive_path).lower()
        if actual_hash != asset.sha256.lower():
            archive_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"LibreHardwareMonitor archive hash mismatch for {asset.asset_name}. "
                f"Expected {asset.sha256}, got {actual_hash}."
            )

    dll_path = bundle_dir / LHM_DLL_NAME
    if not dll_path.exists():
        temp_dir = Path(tempfile.mkdtemp(prefix="lhm-extract-", dir=str(LHM_CACHE_DIR)))
        try:
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(temp_dir)
            extracted_dll_path = temp_dir / LHM_DLL_NAME
            if not extracted_dll_path.exists():
                raise RuntimeError(
                    f"LibreHardwareMonitor bundle {asset.asset_name} does not contain {LHM_DLL_NAME}."
                )
            if bundle_dir.exists():
                shutil.rmtree(bundle_dir)
            shutil.move(str(temp_dir), str(bundle_dir))
        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    _write_manifest(asset, bundle_dir)
    return bundle_dir


def read_lhm_bundle_manifest() -> Optional[dict[str, str]]:
    local_bundle_dir = find_local_lhm_bundle_dir()
    if local_bundle_dir is not None:
        local_manifest_path = local_bundle_dir / LHM_BUNDLE_MANIFEST_NAME
        if local_manifest_path.exists():
            try:
                return json.loads(local_manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
    return _read_manifest()


def _ensure_pythonnet_runtime(bundle_dir: Path) -> None:
    global _PYTHONNET_INITIALIZED
    global _LHM_ASSEMBLY_LOADED

    bundle_dir_str = str(bundle_dir)
    if bundle_dir_str not in sys.path:
        sys.path.append(bundle_dir_str)

    if not _PYTHONNET_INITIALIZED:
        from pythonnet import load

        try:
            load("netfx")
        except RuntimeError:
            pass
        _PYTHONNET_INITIALIZED = True

    import clr

    if not _LHM_ASSEMBLY_LOADED:
        clr.AddReference(str(bundle_dir / LHM_DLL_NAME))
        _LHM_ASSEMBLY_LOADED = True


def _extract_sensor_value(sensor: Any) -> Optional[float]:
    value = getattr(sensor, "Value", None)
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not 0.0 <= numeric <= 150.0:
        return None
    return numeric


def _is_cpu_core_sensor_name(sensor_name: str) -> bool:
    normalized = (sensor_name or "").strip().lower()
    if not normalized:
        return False
    if any(keyword in normalized for keyword in NON_CORE_SENSOR_KEYWORDS):
        return False
    return CPU_CORE_SENSOR_PATTERN.search(normalized) is not None


def _select_hottest_cpu_core_candidate(candidates: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    valid_candidates = [candidate for candidate in candidates if candidate.get("value_c") is not None]
    if not valid_candidates:
        return None
    return max(valid_candidates, key=lambda item: float(item["value_c"]))


def _build_sensor_detail(hardware_name: str, sensor_name: str, sensor_identifier: str) -> str:
    parts = [part for part in (hardware_name, sensor_name, sensor_identifier) if part]
    return " | ".join(parts)


def _update_hardware_tree(hardware: Any) -> None:
    hardware.Update()
    for sub_hardware in getattr(hardware, "SubHardware", []) or []:
        _update_hardware_tree(sub_hardware)


def _iter_hardware_tree(hardware: Any):
    yield hardware
    for sub_hardware in getattr(hardware, "SubHardware", []) or []:
        yield from _iter_hardware_tree(sub_hardware)


def _collect_core_temperature_candidates(computer: Any, temperature_sensor_type: Any) -> list[dict[str, Any]]:
    candidates = []
    for hardware in getattr(computer, "Hardware", []) or []:
        _update_hardware_tree(hardware)
        for current_hardware in _iter_hardware_tree(hardware):
            hardware_name = str(getattr(current_hardware, "Name", "") or "").strip()
            for sensor in getattr(current_hardware, "Sensors", []) or []:
                if getattr(sensor, "SensorType", None) != temperature_sensor_type:
                    continue
                sensor_name = str(getattr(sensor, "Name", "") or "").strip()
                if not _is_cpu_core_sensor_name(sensor_name):
                    continue
                value_c = _extract_sensor_value(sensor)
                sensor_identifier = str(getattr(sensor, "Identifier", "") or "").strip()
                candidates.append(
                    {
                        "value_c": value_c,
                        "sensor_name": sensor_name,
                        "hardware_name": hardware_name,
                        "sensor_identifier": sensor_identifier,
                        "detail": _build_sensor_detail(hardware_name, sensor_name, sensor_identifier),
                    }
                )
    return candidates


def read_cpu_core_max_temperature_sample(attempts: int = 3, settle_delay_sec: float = 0.2) -> Optional[LhmCpuCoreTemperatureSample]:
    bundle_dir = ensure_lhm_bundle_dir()
    _ensure_pythonnet_runtime(bundle_dir)

    from LibreHardwareMonitor.Hardware import Computer, SensorType

    computer = Computer()
    computer.IsCpuEnabled = True
    computer.Open()
    try:
        for attempt_index in range(max(1, attempts)):
            candidates = _collect_core_temperature_candidates(computer, SensorType.Temperature)
            selected = _select_hottest_cpu_core_candidate(candidates)
            if selected is not None:
                return LhmCpuCoreTemperatureSample(
                    value_c=float(selected["value_c"]),
                    detail=str(selected["detail"]),
                    sensor_name=str(selected["sensor_name"]),
                    hardware_name=str(selected["hardware_name"]),
                )
            if attempt_index + 1 < max(1, attempts):
                time.sleep(max(0.0, settle_delay_sec))
    finally:
        try:
            computer.Close()
        except Exception:
            pass

    return None
