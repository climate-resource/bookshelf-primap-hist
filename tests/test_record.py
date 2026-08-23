"""Record and validate every book through the CLI, the way `make run` does.

Each run fetches the raw CSV from Zenodo, roughly 130 MB per version,
so these tests run only when asked: `pytest -m record`.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parent.parent
VERSIONS = ("v2.6", "v2.6.1", "v2.7")

pytestmark = pytest.mark.record


def bookshelf(*args: str, cwd: Path) -> dict:
    result = subprocess.run(
        [sys.executable, "-m", "bookshelf", *args, "--json"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def feedstock(tmp_path_factory):
    """A copy of the feedstock, so a recorded bundle never lands in the checkout."""
    target = tmp_path_factory.mktemp("feedstock")
    for name in ("bookshelf.yaml", "build.py"):
        shutil.copy(ROOT / name, target / name)
    return target


@pytest.mark.parametrize("version", VERSIONS)
def test_record_and_validate(feedstock, version):
    recorded = bookshelf("record", "--force", "--version", version, cwd=feedstock)
    assert recorded["published"] is True
    assert recorded["resources"] == 5
    assert recorded["book_entries"] == 4

    validated = bookshelf("validate", cwd=feedstock)
    assert validated["published"] is True
    assert validated["resources"] == 5
    assert validated["book_entries"] == 4

    manifest = yaml.safe_load((feedstock / "bundle" / "manifest.lock").read_text())
    assert manifest["book"]["version"] == version


def test_record_without_version_names_the_books(feedstock):
    result = subprocess.run(
        [sys.executable, "-m", "bookshelf", "record", "--force"],
        cwd=feedstock,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "NO_COLOR": "1"},
    )
    assert result.returncode != 0
    for version in VERSIONS:
        assert repr(version) in result.stderr + result.stdout
