from datetime import date
from pathlib import Path

import pytest
from bookshelf.publisher import load_record_recipe
from conftest import ROOT, VERSIONS

UPSTREAM_AUTHORS = ("Gütschow, Johannes", "Busch, Daniel", "Pflüger, Mika")


@pytest.fixture(scope="module")
def recipe():
    return load_record_recipe(ROOT / "bookshelf.yaml")


def test_volume(recipe):
    assert recipe.volume.name == "primap-hist"
    assert recipe.build.notebook == Path("build.py")
    assert [m.name for m in recipe.volume.maintainers] == ["Jared Lewis"]
    assert "ghg" in recipe.volume.keywords


def test_declares_every_version_in_order(recipe):
    assert recipe.versions == VERSIONS


@pytest.mark.parametrize("version", VERSIONS)
def test_book_inherits_the_defaults(recipe, version):
    book = recipe.resolve(version)
    discovery = book.discovery

    assert book.visibility == "public"
    assert discovery.title == "PRIMAP-hist"
    assert discovery.publisher == "Potsdam Institute for Climate Impact Research"
    assert discovery.methodology_url == "https://doi.org/10.5194/essd-8-571-2016"
    assert discovery.repository_url == "https://github.com/JGuetschow/PRIMAP-hist"
    assert discovery.citation is not None
    assert discovery.intended_uses is not None
    assert discovery.limitations is not None
    assert tuple(a["name"] for a in book.authors) == UPSTREAM_AUTHORS


@pytest.mark.parametrize(
    ("version", "record", "release_date", "license"),
    [
        ("v2.6", "13752654", date(2024, 9, 13), "CC-BY-4.0"),
        ("v2.6.1", "15016289", date(2025, 3, 13), "CC-BY-4.0"),
        ("v2.7", "17090760", date(2025, 9, 15), "CC-BY-NC-SA-4.0"),
    ],
)
def test_book_states_its_own_release(recipe, version, record, release_date, license):
    book = recipe.resolve(version)
    discovery = book.discovery

    assert book.license == license
    licence_path = license.removeprefix("CC-").removesuffix("-4.0").lower()
    assert (
        discovery.license_url
        == f"https://creativecommons.org/licenses/{licence_path}/4.0/"
    )
    assert discovery.doi == f"10.5281/zenodo.{record}"
    assert discovery.release_date == release_date
    assert discovery.release_url == f"https://zenodo.org/records/{record}"
    assert discovery.description is not None
    assert discovery.description != recipe.defaults.description


@pytest.mark.parametrize("version", VERSIONS)
def test_raw_resource_is_complete(recipe, version):
    raw = recipe.resolve(version).resources["raw"]

    assert raw.type == "tabular"
    assert raw.uri.startswith("https://zenodo.org/api/records/")
    assert raw.uri.endswith("/content")
    assert version.removeprefix("v") in raw.uri
    assert raw.path is None
    assert len(raw.sha256) == 64
