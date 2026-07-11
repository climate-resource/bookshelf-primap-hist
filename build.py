# %% [markdown]
# # PRIMAP-hist
#
# The PRIMAP-hist dataset of historical GHG emissions.

# %% tags=["parameters"]
version = "v2.6"
input_url = (
    "https://zenodo.org/api/records/13752654/files/"
    "Guetschow_et_al_2024a-PRIMAP-hist_v2.6_final_no_rounding_13-Sep-2024.csv/content"
)
input_sha256 = "sha256:54c6d6c2983e8ffd9cb34d2ae7259877f74bb17de52ce135489c19f3c8d51a72"
input_doi = "doi:10.5281/zenodo.13752654"

# %%
import asyncio
import hashlib
import re
from pathlib import Path

import bookshelf_client as bookshelf
import httpx
import pandas as pd
import pycountry
import scmdata

# %%
bs, book = bookshelf.setup(version=version, visibility="public")


# %% [markdown]
# # Fetch
#
# The raw CSV is fetched and its sha256 verified against the declared assertion.


# %%
def fetch_input(url: str, expected_sha256: str) -> Path:
    """Download `url` to a local cache path and verify its sha256."""
    cache = Path(".cache") / f"primap-hist-{version}.csv"
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.exists():
        with httpx.stream("GET", url, follow_redirects=True, timeout=600) as resp:
            resp.raise_for_status()
            with cache.open("wb") as fh:
                for chunk in resp.iter_bytes(1 << 20):
                    fh.write(chunk)

    digest = hashlib.sha256()
    with cache.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    actual = f"sha256:{digest.hexdigest()}"
    if actual != expected_sha256:
        raise ValueError(
            f"hash mismatch for {url}: expected {expected_sha256}, got {actual}"
        )
    return cache


raw_path = fetch_input(input_url, input_sha256)
data_df = pd.read_csv(raw_path)
data_df.head()

# %% [markdown]
# # Process
#
# Minor renames and enrichment.

# %%
col_renames = {
    "scenario (PRIMAP-hist)": "scenario",
    "entity": "variable",
    "area (ISO3)": "region",
    "country": "region",
    "category (IPCC2006_PRIMAP)": "category",
}
data_df_renamed = data_df.rename(col_renames, axis=1)
data_df_renamed["model"] = "PRIMAP-hist"
data_df_renamed["variable"] = "Emissions|" + data_df_renamed["variable"]

data = scmdata.ScmRun(data_df_renamed, lowercase_cols=True)


# %%
def rename_variable(v: str) -> str:
    """Rename variables to be more human readable."""
    return (
        v.replace("KYOTOGHG", "Kyoto GHG")
        .replace("HFCS", "HFCs")
        .replace("PFCS", "PFCs")
        .replace("FGASES", "F-Gases")
    )


data["variable"] = data["variable"].apply(rename_variable)
data["scenario"] = data["scenario"].str.replace("HISTCR", "Historical|Country Reported")
data["scenario"] = data["scenario"].str.replace("HISTTP", "Historical|Third Party")

# %%
pattern = re.compile(r".*\((.*)\)")
pattern_all_but = re.compile(r"(.*) \(.*")


def extract_gwp_context(v: str) -> str | None:
    """Extract the GWP name from a variable."""
    m = re.match(pattern, v)
    return m.group(1) if m else None


def remove_gwp_from_variable(v: str) -> str:
    """Remove the GWP name from a variable."""
    m = re.match(pattern_all_but, v)
    return m.group(1) if m else v


data["gwp_context"] = data["variable"].apply(extract_gwp_context)
data["variable"] = data["variable"].apply(remove_gwp_from_variable)

# %%
regions = {
    "ANNEXI",
    "ANT",
    "AOSIS",
    "BASIC",
    "EARTH",
    "EU27BX",
    "LDC",
    "NONANNEXI",
    "UMBRELLA",
}


def rename_regions(d: scmdata.ScmRun) -> scmdata.ScmRun:
    """Attach a country name to each region code."""
    region = d.get_unique_meta("region", True)
    country_data = pycountry.countries.get(alpha_3=region)
    if country_data is not None:
        d["country"] = country_data.name
    return d


data = data.groupby("region").apply(rename_regions)


# %%
def convert_units(run: scmdata.ScmRun) -> scmdata.ScmRun:
    """Convert units to kt <gas> / yr."""
    unit = run.get_unique_meta("unit", True)
    if not isinstance(unit, str):
        raise TypeError("Unit is not a string")
    variable_dimension = unit.split()[0]
    if variable_dimension == "Gg":
        variable_dimension = unit.split()[1]
    return run.convert_unit(f"kt {variable_dimension} / yr")


data = data.groupby("unit").map(convert_units)

# %%
data_countries = data.filter(region=regions, keep=False)
data_regions = data.filter(region=regions).drop_meta("country")


# %% [markdown]
# # Publish
#
# The raw CSV is re-hosted as a managed resource, and the two processed timeseries
# are registered inside a process activity that declares the raw input as `used`.
#
# A pointer to the Zenodo copy would be the better provenance record, but a bundle
# may not hold both an external pointer and an activity, so lineage wins.


# %%
async def main() -> None:
    """Register the raw input and the two derived timeseries, then publish."""
    raw = await bs.register(
        raw_path,
        type="tabular",
        logical_key=f"primap-hist/raw-{version}",
        metadata={"doi": input_doi, "original_url": input_url},
    )

    async with bs.activity(kind="process", parameters={"version": version}) as act:
        by_country = await act.register(
            data_countries.timeseries().reset_index(),
            type="timeseries",
            logical_key=f"primap-hist/by_country-{version}",
            used=[raw.tracking_id],
        )
        by_region = await act.register(
            data_regions.timeseries().reset_index(),
            type="timeseries",
            logical_key=f"primap-hist/by_region-{version}",
            used=[raw.tracking_id],
        )

    book.attach(by_country, "by_country")
    book.attach(by_region, "by_region")
    book.publish()


asyncio.run(main())
