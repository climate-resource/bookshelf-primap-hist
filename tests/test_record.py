"""Record and validate every book through the CLI, the way `make run` does.

Each record fetches the raw CSV from Zenodo, roughly 130 MB per version,
so those tests run only when asked: `pytest -m record`.
The recorder derives a code reference from git,
so it runs in the checkout and only the bundle goes to a temporary directory.
"""

import json
import os
import subprocess
import sys

import pytest
import yaml
from conftest import ROOT, VERSIONS

EXPECTED_SUMMARY = {"published": True, "resources": 5, "book_entries": 4}


def bookshelf(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [sys.executable, "-m", "bookshelf._cli", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "NO_COLOR": "1"},
    )
    if check:
        assert result.returncode == 0, result.stderr
    return result


def summary(*args: str) -> dict:
    return json.loads(bookshelf(*args, "--json").stdout)


@pytest.mark.record
@pytest.mark.parametrize("version", VERSIONS)
def test_record_and_validate(tmp_path, version):
    bundle = str(tmp_path / "bundle")

    recorded = summary("record", "--force", "--version", version, "--bundle", bundle)
    assert {k: recorded[k] for k in EXPECTED_SUMMARY} == EXPECTED_SUMMARY

    validated = summary("validate", bundle)
    assert {k: validated[k] for k in EXPECTED_SUMMARY} == EXPECTED_SUMMARY

    manifest = yaml.safe_load((tmp_path / "bundle" / "manifest.lock").read_text())
    assert manifest["book"]["version"] == version
    assert manifest["book"]["discovery"]["doi"].startswith("10.5281/zenodo.")


@pytest.mark.record
def test_record_without_version_names_the_books(tmp_path):
    result = bookshelf("record", "--bundle", str(tmp_path / "bundle"), check=False)

    assert result.returncode != 0
    for version in VERSIONS:
        assert repr(version) in result.stderr + result.stdout
