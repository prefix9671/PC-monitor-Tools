import json
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from collectors.libre_hardware_monitor import (  # noqa: E402
    LHM_BUNDLE_MANIFEST_NAME,
    LHM_VENDOR_BUNDLE_DIR,
    ensure_lhm_bundle_dir,
    read_lhm_bundle_manifest,
)


def prepare_lhm_bundle(target_dir: Path = REPO_ROOT / LHM_VENDOR_BUNDLE_DIR) -> Path:
    source_dir = ensure_lhm_bundle_dir()
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    if source_dir.resolve() != target_dir.resolve():
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)
    else:
        target_dir.mkdir(parents=True, exist_ok=True)

    manifest = read_lhm_bundle_manifest() or {}
    manifest_path = target_dir / LHM_BUNDLE_MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return target_dir


def main() -> int:
    bundle_dir = prepare_lhm_bundle()
    print(bundle_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
