# Platform migration PoC: primap-hist v2.6

Throwaway PoC migrating this feedstock to the Bookshelf Platform's shipped
`record → bundle → replay` publish flow (bookshelf-platform issue #256).
Scope: the latest public version, v2.6, only.

The feedstock now consumes the SDK from the `bookshelf` repo's
`feat/adopt-bookshelf-sdk` branch, which folds the platform SDK into the public
`bookshelf` distribution and retires `bookshelf-producer`.
The dependency is pinned to that branch in `pyproject.toml` under
`[tool.uv.sources]` until the SDK is released.

## What the migration is

Two new files replace the old `bookshelf-producer` config and notebook:

- `bookshelf.yaml`: the slim recipe read by the record path, with `collection`,
  `license`, `visibility`, `authors` and `notebook`.
  Version, inputs, outputs and lineage all move *into the build file*.
  They are no longer declared here.
- `build.py`: a standalone Jupytext `.py` build.
  It calls `bookshelf.setup(version=...)` explicitly,
  fetches and hash-verifies the raw CSV,
  runs the same scmdata transform as the old notebook,
  then catalogues the Zenodo input as a pointer,
  registers the outputs inside a `process` activity and publishes.

The `# %%` framing is kept, but it is worth knowing what it does and does not buy.
The record path splits the source on those markers only to chunk the evidence notebook it
captures, and it emits every chunk as a code cell,
so `# %% [markdown]` sections are not rendered as prose in `build.html`.
Their value is the editor experience and the per-step chunking of the captured evidence.
Dropping them is a live option:
a marker-free file records identically, as one cell, and drops the `E402` exemption.

Run it:

```
make run        # record build.py into bundle/ and validate it
make publish    # replay bundle/ to the API, needs a write token
```

Both targets are thin wrappers over the `bookshelf` CLI,
which now ships `record`, `validate` and `publish` subcommands.
The record step is offline and produces a valid 72 MB bundle (`manifest.lock`):
the raw input as a `pointer` with `generated: false`,
both timeseries `generated: true` with `used` edges back to that pointer,
plus the executed notebook and HTML as document entries.

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

- The tests under `tests/` still target the retired `bookshelf-producer` API,
  and `pytest` cannot even collect them.
  They exercised the legacy V1 notebook, which the template update removed,
  so their unit and category assertions would have to be rewritten against the recorded bundle.
  They are left in place pending a decision on the historic versions they cover.
- Replay to staging was blocked by a staging agent-claim sign-in loop
  (bookshelf-platform PR #285).
  The bundle is valid and ready to replay once a write token is available.
