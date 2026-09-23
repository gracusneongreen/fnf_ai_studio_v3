#!/usr/bin/env python3
"""Install FNF-OMNI-VIDEO-V1 weights from Hugging Face or an HTTPS URL."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

ARCHITECTURE_NAME = "FNF-OMNI-VIDEO-V1"
MODEL_DIR = Path(__file__).resolve().parent / ARCHITECTURE_NAME
MANIFEST_PATH = MODEL_DIR / "model_manifest.json"


def load_manifest(path: Path = MANIFEST_PATH) -> Dict[str, Any]:
    """Load and minimally validate the checked-in model manifest."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("architecture") != ARCHITECTURE_NAME:
        raise ValueError(f"unexpected model architecture in {path}")
    weights = payload.get("weights")
    if not isinstance(weights, dict) or not weights.get("filename"):
        raise ValueError(f"missing weights.filename in {path}")
    filename = Path(str(weights["filename"]))
    if filename.name != str(weights["filename"]):
        raise ValueError("weights.filename must be a plain filename")
    return payload


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_checksum(path: Path, expected_sha256: Optional[str]) -> str:
    actual = sha256_file(path)
    if expected_sha256 is not None and actual.lower() != expected_sha256.lower():
        raise ValueError(
            f"SHA-256 mismatch for downloaded weights: expected "
            f"{expected_sha256.lower()}, got {actual.lower()}"
        )
    return actual


def _atomic_install(
    target: Path,
    writer: Callable[[Path], None],
    expected_sha256: Optional[str],
) -> str:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".part", dir=target.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        writer(temporary)
        checksum = _validate_checksum(temporary, expected_sha256)
        os.replace(temporary, target)
        return checksum
    finally:
        temporary.unlink(missing_ok=True)


def install_local_file(
    source: Path, target: Path, expected_sha256: Optional[str] = None
) -> str:
    """Atomically install and optionally verify an existing weight file."""

    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"weight source not found: {source}")
    return _atomic_install(
        target,
        lambda temporary: shutil.copyfile(source, temporary),
        expected_sha256,
    )


def download_https(
    url: str,
    target: Path,
    expected_sha256: Optional[str] = None,
    timeout_seconds: float = 60.0,
) -> str:
    """Download weights over HTTPS and install them atomically."""

    if urllib.parse.urlparse(url).scheme.lower() != "https":
        raise ValueError("weight URL must use HTTPS")

    def write_download(temporary: Path) -> None:
        request = urllib.request.Request(
            url, headers={"User-Agent": "FNF-OMNI-VIDEO-V1/1.0"}
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            if urllib.parse.urlparse(response.geturl()).scheme.lower() != "https":
                raise ValueError("weight download redirected to a non-HTTPS URL")
            with temporary.open("wb") as destination:
                shutil.copyfileobj(response, destination, length=1024 * 1024)

    return _atomic_install(target, write_download, expected_sha256)


def download_huggingface(
    repo_id: str,
    filename: str,
    revision: str,
    target: Path,
    expected_sha256: Optional[str] = None,
) -> str:
    """Download a Hub file through huggingface_hub and install it atomically."""

    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise RuntimeError(
            "huggingface_hub is required; run: pip install -r requirements.txt"
        ) from exc

    cached_path = Path(
        hf_hub_download(repo_id=repo_id, filename=filename, revision=revision)
    )
    return install_local_file(cached_path, target, expected_sha256)


def select_source(
    cli_repo_id: Optional[str],
    cli_url: Optional[str],
    manifest_source: Dict[str, Any],
) -> Tuple[Optional[str], Optional[str]]:
    """Let an explicit CLI source fully override manifest source defaults."""

    if cli_repo_id is not None:
        return cli_repo_id, None
    if cli_url is not None:
        return None, cli_url
    return manifest_source.get("repo_id"), manifest_source.get("url")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"Download {ARCHITECTURE_NAME} LoRA weights."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--repo-id", help="Hugging Face repository ID")
    source.add_argument("--url", help="direct HTTPS .safetensors URL")
    parser.add_argument("--filename", help="weight filename inside the Hub repository")
    parser.add_argument("--revision", help="Hub branch, tag, or commit")
    parser.add_argument("--sha256", help="expected SHA-256 checksum")
    parser.add_argument("--force", action="store_true", help="replace an existing file")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    manifest = load_manifest()
    weights = manifest["weights"]
    source = manifest.get("source") or {}
    target = MODEL_DIR / weights["filename"]
    expected_sha256 = args.sha256 or weights.get("sha256")

    if target.exists() and not args.force:
        if expected_sha256:
            _validate_checksum(target, expected_sha256)
        print(f"Weights already installed at {target}")
        return 0

    repo_id, url = select_source(args.repo_id, args.url, source)
    if repo_id and url:
        parser.error("configure either a Hugging Face repo or an HTTPS URL, not both")
    if not repo_id and not url:
        parser.error(
            "no weight source configured; pass --repo-id or --url, or update "
            f"{MANIFEST_PATH}"
        )

    if repo_id:
        filename = args.filename or source.get("filename") or weights["filename"]
        revision = args.revision or source.get("revision") or "main"
        print(f"Downloading {ARCHITECTURE_NAME} weights from Hugging Face...")
        checksum = download_huggingface(
            repo_id, filename, revision, target, expected_sha256
        )
    else:
        print(f"Downloading {ARCHITECTURE_NAME} weights over HTTPS...")
        checksum = download_https(url, target, expected_sha256)

    print(f"Installed weights at {target}")
    print(f"SHA-256: {checksum}")
    if expected_sha256 is None:
        print("Warning: no expected SHA-256 was configured; record the value above.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
