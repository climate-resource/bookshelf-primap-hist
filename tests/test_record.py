"""Record and validate every book through the CLI, the way `make run` does.

Each run fetches the raw CSV from Zenodo, roughly 130 MB per version,
so these tests run only when asked: `pytest -m record`.
The recorder derives a code reference from git,
so it runs in the checkout and only the bundle goes to a temporary directory.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent
VERSIONS = ("v2.6", "v2.6.1", "v2.7")

pytestmark = pytest.mark.record


def bookshelf(*args: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "bookshelf._cli", *args, "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("version", VERSIONS)
def test_record_and_validate(tmp_path, version):
    bundle = tmp_path / "bundle"

    recorded = bookshelf(
        "record", "--force", "--version", version, "--bundle", str(bundle)
    )
    assert recorded["published"] is True
    assert recorded["resources"] == 5
    assert recorded["book_entries"] == 4

    validated = bookshelf("validate", str(bundle))
    assert validated["published"] is True
    assert validated["resources"] == 5
    assert validated["book_entries"] == 4

    manifest = yaml.safe_load((bundle / "manifest.lock").read_text())
    assert manifest["book"]["version"] == version
    assert manifest["book"]["discovery"]["doi"].startswith("10.5281/zenodo.")


def test_record_without_version_names_the_books(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bookshelf._cli",
            "record",
            "--bundle",
            str(tmp_path / "bundle"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "NO_COLOR": "1"},
    )
    assert result.returncode != 0
    for version in VERSIONS:
        assert repr(version) in result.stderr + result.stdout
