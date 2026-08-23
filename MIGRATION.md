# Platform migration PoC: primap-hist v2.6

Throwaway PoC migrating this feedstock to the Bookshelf Platform's shipped
`record → bundle → replay` publish flow (bookshelf-platform issue #256).
Scope: the three current public versions, v2.6, v2.6.1 and v2.7.

The feedstock now consumes the SDK from the `bookshelf` repo's
`feat/adopt-bookshelf-sdk` branch, which folds the platform SDK into the public
`bookshelf` distribution and retires `bookshelf-producer`.
The dependency is pinned to that branch in `pyproject.toml` under
`[tool.uv.sources]` until the SDK is released.

## What the migration is

Two files replace the old `bookshelf-producer` config and notebook:

- `bookshelf.yaml`: the sectioned recipe.
  `volume:` names the collection, its maintainers and its keywords.
  `defaults:` holds what every book shares: title, description, publisher, citation,
  the upstream authors, the URLs, the visibility and the `type` of the raw resource.
  `books:` lists one entry per PRIMAP-hist version.
  Each states only its licence, DOI, release date, release notes
  and the URL and sha256 of the raw CSV.
  Licence, visibility and discovery metadata are merged field by field, and the book wins.
- `build.py`: a standalone Jupytext `.py` build holding only the processing.
  It calls `bookshelf.setup()` once, with no version,
  reads the raw CSV through `build.use("raw")`,
  which fetches, verifies the sha256 and catalogues the Zenodo file as a pointer,
  runs the same scmdata transform as the old notebook,
  then writes both timeseries with `build.book.write(..., used=[raw])` and publishes.

The `# %%` framing is kept, but it is worth knowing what it does and does not buy.
The record path splits the source on those markers only to chunk the evidence notebook it
captures, and it emits every chunk as a code cell,
so `# %% [markdown]` sections are not rendered as prose in `build.html`.
Their value is the editor experience and the per-step chunking of the captured evidence.
Dropping them is a live option:
a marker-free file records identically, as one cell.

Run it:

```
make run VERSION=v2.6   # record one book into bundle/ and validate it
make publish            # replay bundle/ to the API, needs a write token
```

`--version` is required.
The recipe names no default, so a version is stated exactly once, on the command line,
and `make run` passes `VERSION`, which the Makefile defaults to v2.7.
Each version has to be recorded and replayed in its own run,
because a bundle holds one book edition.

Both targets are thin wrappers over the `bookshelf` CLI,
which now ships `record`, `validate` and `publish` subcommands.
The record step is offline and produces a valid bundle (`manifest.lock`):
the raw input as a `pointer` with `generated: false`,
both timeseries `generated: true` with `used` edges back to that pointer,
plus the executed notebook and HTML as document entries.

### Where the metadata came from

Every discovery field was taken from the three Zenodo records and the ESSD paper
(Gütschow et al. 2016, doi:10.5194/essd-8-571-2016).

- The authors are the Zenodo creators, with their ORCIDs.
  They sit under `defaults:` and are overridden on v2.7,
  where Gütschow's affiliation changed.
  The recipe has no `authors` on a resource, so they cannot be attached to the raw CSV itself.
  Jared is a `maintainer` on the volume rather than an author.
- The licence is per record and differs:
  v2.6 and v2.6.1 are `CC-BY-4.0`, and v2.7 is `CC-BY-NC-SA-4.0`.
  The earlier PoC declared `CC-BY-NC` for all three, which was wrong on both counts.
- `release_date` is the Zenodo publication date, not the date in the file name.
  v2.7's file is dated 22 August 2025 and the record was published on 15 September 2025.
- The platform's `volume_metadata.yaml` carries a `primap-hist` block that mixes
  the v2.6 DOI into a v2.7 description.
  The recipe supersedes it.

### Identifiers

The `uuid5` tracking ids and activity id from the earlier PoC are gone.
The bundle never stored them, so the recorded bytes were already independent of them,
and the platform assigns tracking ids on replay.

## Where it hurt

Concrete friction found while migrating.
Each is a candidate fix for the SDK, the copier template or the public feedstock CI actions.

1. **The ticket's ADR-0007 wording is stale.**
   `bookshelf.yaml → bookshelf.lock` (the full `books[]`/`inputs`/`outputs` recipe)
   is now the legacy path.
   The shipped default is `record → bundle → manifest.lock → replay` (ADR 0011).
   Two incompatible `bookshelf.yaml` schemas still ship in one package:
   the full recipe (`publisher/recipe.py`, pydantic, `extra="forbid"`, `books[]` required)
   and the slim record recipe (`publisher/record.py`, four keys).
   A slim file is rejected by the full loader,
   and a full file has its `books:` block silently ignored by the slim loader.

2. **Notebook capture is mandatory.**
   The recipe key is `notebook:` and the record path always captures an executed
   `.ipynb` plus its HTML render and attaches both as book entries,
   so `[publish]` (papermill, nbconvert) is required even for a build file with no cells.
   Making the capture opt-in would let a feedstock choose a plain script.

3. **Build parameters must be top-level module assignments.**
   `-p name=value` works by seeding module globals and dropping the matching top-level
   assignment before execution.
   A build file that wraps its work in `def main()` cannot be parameterised,
   so the record contract quietly forbids the obvious script shape.

4. **A managed resource cannot be recorded outside an activity.**
   The producer facade exposes `activity()`, `register_external()` and `draft_book()`,
   but no top-level `register()`,
   and everything registered through an activity is forced to `generated: true`.
   So a re-hosted raw input can only be recorded as an output of the build that consumed it,
   which is the wrong lineage claim.
   Using an external pointer sidesteps this,
   but a feedstock whose input has no stable public URL has no correct option.

5. **Zenodo publishes md5, the recipe wants sha256.**
   Every input hash upstream is `md5:`, but ingest and record hashes are `sha256:<hex>`.
   Getting the sha256 means downloading the full file first
   (132 MB here, roughly three minutes over a home connection).
   There is no metadata shortcut.
   Feedstock CI should cache raw inputs by content hash.

### Resolved by the SDK adoption branch

- **`-p key=value` build parameters are no longer dropped.**
  The record path strips the in-file default assignment for any overridden name
  before executing the cell,
  so `-p version=v2.6` now takes effect.
  Previously it was silently ignored and the book was recorded under the wrong version.
- **The CLI no longer needs an extra to import.**
  `typer` is a core dependency of the SDK rather than an optional one.
- **`record`, `validate` and `publish` are CLI subcommands.**
  The publish flow was a Python API only, so every feedstock had to carry its own driver.
  The copier template now drives the shipped commands from the `Makefile` and from CI,
  and this feedstock no longer carries a publishing script of its own.
- **External-pointer lineage is expressable.**
  A bundle may now hold both a pointer and an activity,
  so the raw CSV is catalogued at its Zenodo URL
  and the outputs declare it as `used`.
  This drops the bundle from 198 MB to 72 MB and removes a 132 MB re-upload.
- **`used=[resource]` is accepted.**
  `UsedInput` covers any object carrying a `tracking_id`,
  so passing `.tracking_id` by hand is no longer required.

## Not covered

- The shared `feedstock-ci` and `feedstock-publish` workflows in `copier-bookshelf-dataset`
  run a bare `bookshelf record`, which now exits non-zero because `--version` is required.
  CI for this feedstock stays red until those workflows take a version.
- Replay to staging was blocked by a staging agent-claim sign-in loop
  (bookshelf-platform PR #285).
  The bundle is valid and ready to replay once a write token is available.
