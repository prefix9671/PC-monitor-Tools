import ctypes
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


PAWNIO_RELEASE_API_URL = "https://api.github.com/repos/namazso/PawnIO.Setup/releases/latest"
PAWNIO_CACHE_DIR = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "PC-monitor-Tools" / "pawnio-cache"
PAWNIO_MANIFEST_PATH = PAWNIO_CACHE_DIR / "pawnio-manifest.json"
PAWNIO_SETUP_NAME = "PawnIO_setup.exe"
PAWNIO_BUNDLE_DIRNAME = "pawnio-bundle"
PAWNIO_BUNDLE_MANIFEST_NAME = "pawnio-manifest.json"
PAWNIO_VENDOR_BUNDLE_DIR = Path(".artifacts") / "vendor" / PAWNIO_BUNDLE_DIRNAME
PAWNIO_SUCCESS_RETURN_CODES = (0, 3010)


@dataclass(frozen=True)
class PawnIoReleaseAsset:
    version: str
    asset_name: str
    download_url: str
    sha256: Optional[str]
    html_url: str


@dataclass(frozen=True)
class PawnIoInstallResult:
    setup_path: Path
    returncode: Optional[int]
    installed_version: Optional[str]
    reboot_required: bool
    ok: bool
    error: Optional[str] = None


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
    if not PAWNIO_MANIFEST_PATH.exists():
        return None
    try:
        return json.loads(PAWNIO_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_manifest(asset: PawnIoReleaseAsset, setup_path: Path) -> None:
    payload = {
        "version": asset.version,
        "asset_name": asset.asset_name,
        "download_url": asset.download_url,
        "sha256": asset.sha256 or "",
        "html_url": asset.html_url,
        "setup_path": str(setup_path),
    }
    PAWNIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PAWNIO_MANIFEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


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


def _sanitize_version(version: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", version or "latest")


def _select_release_asset(release_payload: dict[str, Any]) -> PawnIoReleaseAsset:
    assets = release_payload.get("assets") or []
    selected = None

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        if str(asset.get("name", "")).lower() == PAWNIO_SETUP_NAME.lower():
            selected = asset
            break

    if selected is None:
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name", ""))
            if "pawnio" in name.lower() and name.lower().endswith(".exe"):
                selected = asset
                break

    if selected is None:
        raise RuntimeError("PawnIO latest release does not expose a usable setup executable.")

    digest = str(selected.get("digest", "")).strip()
    sha256_value = None
    if digest.lower().startswith("sha256:"):
        sha256_value = digest.split(":", 1)[1]

    return PawnIoReleaseAsset(
        version=str(release_payload.get("tag_name") or release_payload.get("name") or "latest"),
        asset_name=str(selected.get("name") or PAWNIO_SETUP_NAME),
        download_url=str(selected.get("browser_download_url") or ""),
        sha256=sha256_value,
        html_url=str(release_payload.get("html_url") or ""),
    )


def _is_valid_setup_path(setup_path: Optional[Path]) -> bool:
    if setup_path is None:
        return False
    try:
        return setup_path.exists() and setup_path.is_file() and setup_path.stat().st_size > 0
    except OSError:
        return False


def _cached_setup_path_from_manifest() -> Optional[Path]:
    manifest = _read_manifest()
    if manifest is None:
        return None

    setup_path = Path(manifest.get("setup_path", "")).expanduser()
    if _is_valid_setup_path(setup_path):
        return setup_path
    return None


def _local_pawnio_setup_candidates() -> list[Path]:
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / PAWNIO_BUNDLE_DIRNAME / PAWNIO_SETUP_NAME)

    executable_dir = Path(sys.executable).resolve().parent
    candidates.append(executable_dir / PAWNIO_BUNDLE_DIRNAME / PAWNIO_SETUP_NAME)

    repo_root = Path(__file__).resolve().parents[1]
    candidates.append(repo_root / PAWNIO_VENDOR_BUNDLE_DIR / PAWNIO_SETUP_NAME)
    return candidates


def find_local_pawnio_setup_path() -> Optional[Path]:
    for candidate in _local_pawnio_setup_candidates():
        if _is_valid_setup_path(candidate):
            return candidate
    return None


def ensure_pawnio_setup_path() -> Path:
    local_setup_path = find_local_pawnio_setup_path()
    if local_setup_path is not None:
        return local_setup_path

    cached_setup_path = _cached_setup_path_from_manifest()
    if cached_setup_path is not None:
        return cached_setup_path

    PAWNIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    release_payload = _request_json(PAWNIO_RELEASE_API_URL)
    asset = _select_release_asset(release_payload)

    setup_dir = PAWNIO_CACHE_DIR / _sanitize_version(asset.version)
    setup_path = setup_dir / PAWNIO_SETUP_NAME

    if not setup_path.exists():
        _download_file(asset.download_url, setup_path)

    if asset.sha256:
        actual_hash = _sha256_file(setup_path).lower()
        if actual_hash != asset.sha256.lower():
            setup_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"PawnIO setup hash mismatch for {asset.asset_name}. "
                f"Expected {asset.sha256}, got {actual_hash}."
            )

    _write_manifest(asset, setup_path)
    return setup_path


def read_pawnio_bundle_manifest() -> Optional[dict[str, str]]:
    local_setup_path = find_local_pawnio_setup_path()
    if local_setup_path is not None:
        local_manifest_path = local_setup_path.parent / PAWNIO_BUNDLE_MANIFEST_NAME
        if local_manifest_path.exists():
            try:
                return json.loads(local_manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
    return _read_manifest()


def read_pawnio_installed_version() -> Optional[str]:
    if sys.platform != "win32":
        return None

    try:
        import winreg
    except ImportError:
        return None

    subkey_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PawnIO"
    views = [0]
    for view_name in ("KEY_WOW64_64KEY", "KEY_WOW64_32KEY"):
        view = getattr(winreg, view_name, None)
        if view is not None and view not in views:
            views.append(view)

    for view in views:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, subkey_path, 0, winreg.KEY_READ | view) as key:
                value, _ = winreg.QueryValueEx(key, "DisplayVersion")
                version = str(value).strip()
                if version:
                    return version
        except OSError:
            continue

    return None


def is_pawnio_installed() -> bool:
    return read_pawnio_installed_version() is not None


def is_current_process_elevated() -> Optional[bool]:
    if sys.platform != "win32":
        return None
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return None


def install_pawnio(setup_path: Optional[Path] = None) -> PawnIoInstallResult:
    resolved_setup_path = Path(setup_path) if setup_path is not None else ensure_pawnio_setup_path()
    try:
        completed = subprocess.run([str(resolved_setup_path), "-install"], check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return PawnIoInstallResult(
            setup_path=resolved_setup_path,
            returncode=None,
            installed_version=read_pawnio_installed_version(),
            reboot_required=False,
            ok=False,
            error=str(exc),
        )

    reboot_required = completed.returncode == 3010
    ok = completed.returncode in PAWNIO_SUCCESS_RETURN_CODES
    return PawnIoInstallResult(
        setup_path=resolved_setup_path,
        returncode=completed.returncode,
        installed_version=read_pawnio_installed_version(),
        reboot_required=reboot_required,
        ok=ok,
    )
