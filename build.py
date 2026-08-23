# %% [markdown]
# # PRIMAP-hist
#
# The PRIMAP-hist dataset of historical GHG emissions.

# %%
import re

import bookshelf
import pandas as pd
import pycountry
import scmdata

# %% [markdown]
# # Fetch
#
# The raw CSV is fetched, verified against the sha256 in the recipe and catalogued
# as an external pointer at its Zenodo URL, so the platform never re-hosts it.

# %%
build = bookshelf.setup()
raw = build.use("raw")
data_df = pd.read_csv(raw.path)
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
gwp_in_brackets = re.compile(r".*\((.*)\)")
name_before_brackets = re.compile(r"(.*) \(.*")


def extract_gwp_context(v: str) -> str | None:
    """Extract the GWP name from a variable."""
    m = gwp_in_brackets.match(v)
    return m.group(1) if m else None


def remove_gwp_from_variable(v: str) -> str:
    """Remove the GWP name from a variable."""
    m = name_before_brackets.match(v)
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

# %%
build.book.write(
    "by_country",
    data_countries.timeseries().reset_index(),
    type="timeseries",
    used=[raw],
)
build.book.write(
    "by_region",
    data_regions.timeseries().reset_index(),
    type="timeseries",
    used=[raw],
)
build.book.publish()
