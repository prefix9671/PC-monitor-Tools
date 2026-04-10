import ctypes
import hashlib
import json
import os
import subprocess
import tempfile
import time
import urllib.request
import winreg
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from collectors.subprocess_utils import run_text_capture

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
CACHE_DIR = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "PC-monitor-Tools" / "dcm-cache"
UNINSTALL_PATHS = (
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
)
DCM_NAMESPACE = "root\\dcim\\sysman"


@dataclass(frozen=True)
class DcmPackage:
    name: str
    version: str
    driver_id: str
    download_url: str
    sha256: str
    model_tokens: tuple[str, ...]


@dataclass(frozen=True)
class DcmBootstrapResult:
    manufacturer: str
    model: str
    supported_model: bool
    package_name: Optional[str]
    installed_version: Optional[str]
    namespace_available: bool
    attempted_install: bool
    reboot_required: bool
    installer_path: Optional[str]
    message: str


LEGACY_PRECISION_PACKAGE = DcmPackage(
    name="legacy_precision_tower",
    version="10.8.0.284",
    driver_id="KJ0VF",
    download_url="https://dl.dell.com/FOLDER08796448M/3/Dell-Command-Monitor_KJ0VF_WIN_10.8.0.284_A00_02.EXE",
    sha256="69baa7ca4ffebe632310c7aaf019703c70c894c26c21a5201f2d9160247bff7a",
    model_tokens=("5820", "7820", "7920"),
)

MODERN_PRECISION_PACKAGE = DcmPackage(
    name="modern_precision_tower",
    version="10.12.3.28",
    driver_id="YYKP6",
    download_url="https://dl.dell.com/FOLDER13809673M/1/Dell-Command-Monitor_YYKP6_WIN64_10.12.3.28_A00.EXE",
    sha256="0e574459faf7e0e00367da87254ed5fb9fee7a2a75ead0174dccce76971145c3",
    model_tokens=("5860", "7860", "7865", "7875", "7960"),
)

DCM_PACKAGES = (
    LEGACY_PRECISION_PACKAGE,
    MODERN_PRECISION_PACKAGE,
)


def _run_powershell(script: str, timeout_sec: float = 5.0) -> str:
    try:
        completed = run_text_capture(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            timeout=timeout_sec,
            creationflags=CREATE_NO_WINDOW,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return ""

    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _normalize_json_record(payload: str) -> dict[str, str]:
    payload = (payload or "").strip()
    if not payload:
        return {}
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict):
        return {str(key): str(value) for key, value in data.items()}
    return {}


def get_system_identity() -> tuple[str, str]:
    script = """
    Get-CimInstance Win32_ComputerSystem -ErrorAction Stop |
        Select-Object Manufacturer, Model |
        ConvertTo-Json -Compress
    """
    record = _normalize_json_record(_run_powershell(script))
    return record.get("Manufacturer", ""), record.get("Model", "")


def _is_target_precision_workstation(manufacturer: str, model: str) -> bool:
    manufacturer_lower = (manufacturer or "").lower()
    model_lower = (model or "").lower()
    if "dell" not in manufacturer_lower:
        return False
    if "precision" not in model_lower:
        return False
    return any(token in model_lower for package in DCM_PACKAGES for token in package.model_tokens)


def resolve_dcm_package(manufacturer: str, model: str) -> Optional[DcmPackage]:
    if not _is_target_precision_workstation(manufacturer, model):
        return None

    model_lower = (model or "").lower()
    for package in DCM_PACKAGES:
        if any(token in model_lower for token in package.model_tokens):
            return package
    return None


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def get_installed_dcm_version() -> Optional[str]:
    for uninstall_path in UNINSTALL_PATHS:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uninstall_path) as root_key:
                subkey_count = winreg.QueryInfoKey(root_key)[0]
                for index in range(subkey_count):
                    subkey_name = winreg.EnumKey(root_key, index)
                    try:
                        with winreg.OpenKey(root_key, subkey_name) as subkey:
                            display_name = str(winreg.QueryValueEx(subkey, "DisplayName")[0])
                            if "Dell Command | Monitor" not in display_name and "Dell Command Monitor" not in display_name:
                                continue
                            return str(winreg.QueryValueEx(subkey, "DisplayVersion")[0])
                    except OSError:
                        continue
        except OSError:
            continue
    return None


def is_dcm_namespace_available(timeout_sec: float = 2.0) -> bool:
    script = f"""
    if (Get-CimClass -Namespace {DCM_NAMESPACE} -ClassName DCIM_NumericSensor -ErrorAction SilentlyContinue) {{
        'present'
    }}
    """
    return _run_powershell(script, timeout_sec=timeout_sec).strip().lower() == "present"


def should_use_dell_command_monitor_provider(timeout_sec: float = 2.0) -> bool:
    manufacturer, model = get_system_identity()
    if resolve_dcm_package(manufacturer, model) is None:
        return False
    return is_dcm_namespace_available(timeout_sec=timeout_sec)


def _download_file(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response, destination.open("wb") as output:
        output.write(response.read())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prepare_installer(package: DcmPackage) -> Path:
    file_name = Path(package.download_url).name
    destination = CACHE_DIR / file_name
    if not destination.exists() or _sha256_file(destination).lower() != package.sha256.lower():
        _download_file(package.download_url, destination)
    actual_hash = _sha256_file(destination).lower()
    if actual_hash != package.sha256.lower():
        raise RuntimeError(
            f"Downloaded Dell Command | Monitor installer hash mismatch for {file_name}. "
            f"Expected {package.sha256}, got {actual_hash}."
        )
    return destination


def _run_installer(installer_path: Path) -> tuple[int, str, str]:
    completed = run_text_capture(
        [str(installer_path), "/s"],
        timeout=900,
        creationflags=CREATE_NO_WINDOW,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _wait_for_namespace(tries: int = 12, sleep_sec: float = 5.0) -> bool:
    for _ in range(tries):
        if is_dcm_namespace_available():
            return True
        time.sleep(sleep_sec)
    return False


def ensure_dcm_ready(auto_install: bool = True) -> DcmBootstrapResult:
    manufacturer, model = get_system_identity()
    package = resolve_dcm_package(manufacturer, model)
    installed_version = get_installed_dcm_version()
    namespace_available = is_dcm_namespace_available()

    if package is None:
        return DcmBootstrapResult(
            manufacturer=manufacturer,
            model=model,
            supported_model=False,
            package_name=None,
            installed_version=installed_version,
            namespace_available=namespace_available,
            attempted_install=False,
            reboot_required=False,
            installer_path=None,
            message=f"DCM bootstrap skipped: non-target system ({manufacturer or 'Unknown'} / {model or 'Unknown'}).",
        )

    if namespace_available:
        return DcmBootstrapResult(
            manufacturer=manufacturer,
            model=model,
            supported_model=True,
            package_name=package.name,
            installed_version=installed_version,
            namespace_available=True,
            attempted_install=False,
            reboot_required=False,
            installer_path=None,
            message=(
                f"Dell Command | Monitor ready for {model}. "
                f"Namespace {DCM_NAMESPACE} is available."
            ),
        )

    if not auto_install:
        return DcmBootstrapResult(
            manufacturer=manufacturer,
            model=model,
            supported_model=True,
            package_name=package.name,
            installed_version=installed_version,
            namespace_available=False,
            attempted_install=False,
            reboot_required=False,
            installer_path=None,
            message=(
                f"Dell target system detected ({model}) but DCM namespace is not available. "
                "Continuing with fallback temperature providers."
            ),
        )

    if not is_admin():
        installer_path = None
        download_note = ""
        try:
            installer_path = str(_prepare_installer(package))
            download_note = f" Official installer cached at {installer_path}."
        except Exception as exc:
            download_note = f" Installer download failed: {exc}."
        return DcmBootstrapResult(
            manufacturer=manufacturer,
            model=model,
            supported_model=True,
            package_name=package.name,
            installed_version=installed_version,
            namespace_available=False,
            attempted_install=False,
            reboot_required=False,
            installer_path=installer_path,
            message=(
                f"Dell target system detected ({model}) but administrator rights are required to install "
                f"Dell Command | Monitor.{download_note} "
                "Continuing with fallback temperature providers until the next elevated run."
            ),
        )

    try:
        installer_path = _prepare_installer(package)
        exit_code, stdout_text, stderr_text = _run_installer(installer_path)
    except Exception as exc:
        return DcmBootstrapResult(
            manufacturer=manufacturer,
            model=model,
            supported_model=True,
            package_name=package.name,
            installed_version=installed_version,
            namespace_available=False,
            attempted_install=True,
            reboot_required=False,
            installer_path=None,
            message=(
                f"Dell target system detected ({model}) but DCM install failed: {exc}. "
                "Continuing with fallback temperature providers."
            ),
        )

    namespace_after_install = _wait_for_namespace()
    installed_after_install = get_installed_dcm_version()
    reboot_required = not namespace_after_install

    if namespace_after_install:
        return DcmBootstrapResult(
            manufacturer=manufacturer,
            model=model,
            supported_model=True,
            package_name=package.name,
            installed_version=installed_after_install,
            namespace_available=True,
            attempted_install=True,
            reboot_required=False,
            installer_path=str(installer_path),
            message=(
                f"Dell Command | Monitor installed for {model}. "
                f"Namespace {DCM_NAMESPACE} is now available."
            ),
        )

    details = stderr_text or stdout_text or f"installer exit code {exit_code}"
    return DcmBootstrapResult(
        manufacturer=manufacturer,
        model=model,
        supported_model=True,
        package_name=package.name,
        installed_version=installed_after_install,
        namespace_available=False,
        attempted_install=True,
        reboot_required=reboot_required,
        installer_path=str(installer_path),
        message=(
            f"Dell target system detected ({model}) and DCM install was attempted, "
            f"but namespace {DCM_NAMESPACE} is still unavailable. Details: {details}. "
            "Continuing with fallback temperature providers."
        ),
    )
