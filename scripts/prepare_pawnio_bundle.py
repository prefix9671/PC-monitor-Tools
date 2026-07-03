import json
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from collectors.pawnio_package import (  # noqa: E402
    PAWNIO_BUNDLE_MANIFEST_NAME,
    PAWNIO_SETUP_NAME,
    PAWNIO_VENDOR_BUNDLE_DIR,
    ensure_pawnio_setup_path,
    read_pawnio_bundle_manifest,
)


def prepare_pawnio_bundle(target_dir: Path = REPO_ROOT / PAWNIO_VENDOR_BUNDLE_DIR) -> Path:
    source_path = ensure_pawnio_setup_path()
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    if source_path.parent.resolve() != target_dir.resolve():
        if target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_dir / PAWNIO_SETUP_NAME)
    else:
        target_dir.mkdir(parents=True, exist_ok=True)

    manifest = read_pawnio_bundle_manifest() or {}
    manifest["setup_filename"] = PAWNIO_SETUP_NAME
    manifest_path = target_dir / PAWNIO_BUNDLE_MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return target_dir


def main() -> int:
    bundle_dir = prepare_pawnio_bundle()
    print(bundle_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
