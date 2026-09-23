import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from models.download_weights import (
    ARCHITECTURE_NAME,
    download_https,
    install_local_file,
    load_manifest,
    select_source,
)


class WeightDownloaderTests(unittest.TestCase):
    def test_manifest_names_pipeline_and_config(self):
        manifest = load_manifest()
        self.assertEqual(manifest["architecture"], ARCHITECTURE_NAME)
        self.assertEqual(manifest["pipeline_class"], "FNFOmniVideoV1Pipeline")
        self.assertEqual(manifest["config_class"], "FNFOmniVideoV1Config")
        self.assertEqual(
            manifest["weights"]["filename"], "fnf-omni-video-v1.safetensors"
        )
        preview_manifest_path = (
            Path(__file__).parents[1]
            / "models"
            / "FNF-OMNI-PREVIEW-LITE"
            / "model_manifest.json"
        )
        preview_manifest = json.loads(preview_manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(preview_manifest["engine_class"], "FNFOmniPreviewEngine")
        self.assertIsNone(preview_manifest["weights"])

    def test_local_install_is_atomic_and_checksum_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.safetensors"
            target = root / "model" / "installed.safetensors"
            payload = b"synthetic test weights"
            source.write_bytes(payload)
            expected = hashlib.sha256(payload).hexdigest()

            actual = install_local_file(source, target, expected)

            self.assertEqual(actual, expected)
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(list(target.parent.glob("*.part")), [])

    def test_direct_download_rejects_non_https_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "weights.safetensors"
            with self.assertRaisesRegex(ValueError, "must use HTTPS"):
                download_https("http://example.com/weights", target)

    def test_cli_source_fully_overrides_manifest_source(self):
        manifest_source = {
            "repo_id": "manifest/repo",
            "url": "https://example.com/manifest.safetensors",
        }
        self.assertEqual(
            select_source("cli/repo", None, manifest_source),
            ("cli/repo", None),
        )
        self.assertEqual(
            select_source(None, "https://example.com/cli.safetensors", manifest_source),
            (None, "https://example.com/cli.safetensors"),
        )


if __name__ == "__main__":
    unittest.main()
