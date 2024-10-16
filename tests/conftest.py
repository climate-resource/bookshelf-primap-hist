"""
Re-useable fixtures etc. for tests

See https://docs.pytest.org/en/7.1.x/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files
"""

import shutil

import pytest
from bookshelf.utils import create_local_cache


@pytest.fixture(scope="function", autouse=True)
def local_bookshelf(tmpdir, monkeypatch):
    monkeypatch.setenv("BOOKSHELF_CACHE_LOCATION", str(tmpdir))
    fname = create_local_cache(tmpdir)

    yield fname

    shutil.rmtree(fname)
