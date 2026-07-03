import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from collectors.pawnio_package import (  # noqa: E402
    PAWNIO_SETUP_NAME,
    ensure_pawnio_setup_path,
    _select_release_asset,
)


class TestPawnIoPackageResolution(unittest.TestCase):
    def test_ensure_pawnio_setup_path_prefers_local_bundle_without_network(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_path = Path(temp_dir) / "pawnio-bundle" / PAWNIO_SETUP_NAME
            setup_path.parent.mkdir(parents=True, exist_ok=True)
            setup_path.write_bytes(b"fake-setup")

            with patch(
                "collectors.pawnio_package._local_pawnio_setup_candidates",
                return_value=[setup_path],
            ), patch(
                "collectors.pawnio_package._request_json",
                side_effect=AssertionError("Network access should not be attempted when local PawnIO setup exists."),
            ):
                resolved = ensure_pawnio_setup_path()

            self.assertEqual(setup_path, resolved)

    def test_select_release_asset_prefers_pawnio_setup_exe(self):
        payload = {
            "tag_name": "2.2.0",
            "html_url": "https://github.com/namazso/PawnIO.Setup/releases/tag/2.2.0",
            "assets": [
                {"name": "notes.txt", "browser_download_url": "https://example.invalid/notes.txt"},
                {
                    "name": PAWNIO_SETUP_NAME,
                    "browser_download_url": "https://example.invalid/PawnIO_setup.exe",
                    "digest": "sha256:" + ("a" * 64),
                },
            ],
        }

        asset = _select_release_asset(payload)

        self.assertEqual("2.2.0", asset.version)
        self.assertEqual(PAWNIO_SETUP_NAME, asset.asset_name)
        self.assertEqual("a" * 64, asset.sha256)


if __name__ == "__main__":
    unittest.main()
