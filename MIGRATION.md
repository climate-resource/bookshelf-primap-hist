# Platform migration PoC — primap-hist v2.6

Throwaway PoC migrating this feedstock to the Bookshelf Platform's shipped
`record → bundle → replay` publish flow (bookshelf-platform issue #256).
Scope: the latest public version, v2.6, only.

## What the migration is

Two new files replace the old `bookshelf-producer` config + notebook:

- `bookshelf.yaml` — the slim recipe read by `bookshelf record`: `collection`,
  `license`, `authors`, `notebook`. Version, visibility, inputs, outputs, and
  lineage all move *into the build file* — they are no longer declared here.
- `build.py` — a standalone Jupytext `.py` build. It calls
  `bookshelf.setup(version=..., visibility=...)` explicitly, fetches and
  hash-verifies the raw CSV, runs the same scmdata transform as the old
  notebook, then registers outputs inside a `process` activity and publishes.

Run it:

```
bookshelf record build.py --recipe bookshelf.yaml --bundle bundle
bookshelf publish bundle/          # replay to the API (needs a write token)
```

The record step is offline and produced a valid 198 MB bundle
(`manifest.lock`): raw input `generated: false`, both timeseries
`generated: true` with `used` edges back to the raw resource, plus the
executed notebook + HTML as document entries.

## Where it hurt

Concrete friction found while migrating; each is a candidate fix for the
copier template or the public feedstock CI actions.

1. **The ticket's ADR-0007 wording is stale.** `bookshelf.yaml → bookshelf.lock`
   (the full `books[]`/`inputs`/`outputs` recipe) is now the *legacy* path
   behind `bookshelf publish --record`. The shipped default is
   `record → bundle → manifest.lock → replay` (ADR 0011). Two *incompatible*
   `bookshelf.yaml` schemas now ship in one package: the full recipe
   (`recipe.py`, pydantic, `extra="forbid"`, `books[]` required) and the slim
   record recipe (`recording.py`, four keys). A slim file is rejected by the
   full loader; a full file has its `books:` block silently ignored by the slim
   loader.

2. **`-p key=value` build parameters are silently dropped.** A `# %% tags=["parameters"]`
   cell is *not* treated as a papermill parameters cell by the `.py` record
   path, so `--parameter version=v2.6` did not override the in-file default and
   the book was recorded as the wrong version with no error. The build file must
   hardcode its own values, or read them another way. This clobbers book
   identity silently — the sharpest trap.

3. **The `bookshelf` CLI crashes without the `cli` extra.** `[project.scripts]`
   declares `bookshelf` unconditionally, but `typer` lives in the optional
   `cli` extra, so a bare install yields a console script that dies on import
   (`ModuleNotFoundError: typer`). Feedstock CI must install
   `bookshelf-client[cli,publish,dataframes]`.

4. **External-pointer lineage is unexpressable on the record path.** A bundle is
   *either* a pointer bundle *or* an activity bundle — `set_activity` refuses if
   a pointer exists and vice versa. So the ideal provenance (raw CSV as an
   external pointer to Zenodo, outputs derived from it) can't be recorded; the
   PoC re-hosts the raw CSV as a `managed` resource instead, trading a 132 MB
   re-upload for working lineage.

5. **`used=[artifact]` is rejected — you must pass `.tracking_id`.**
   `bs.register(...)` returns an `Artifact`, but `activity.register(..., used=...)`
   only accepts a `UUID`/`BookResource`, so `used=[raw]` raises a validation
   error; `used=[raw.tracking_id]` is required. Easy to get wrong.

6. **Zenodo publishes md5; the recipe wants sha256.** Every input hash upstream
   is `md5:`, but ingest/record hashes are `sha256:<hex>`. Getting the sha256
   means downloading the full file first (132 MB here, ~3m over a home
   connection) — there is no metadata shortcut. Feedstock CI should cache raw
   inputs by content hash.

## Not covered

- The confidential `v2.5_beta5` input (`file://data/...csv`) and the historic
  backfill were out of scope; the `file://` and `doi:` URL schemes are not
  handled by the record/ingest fetcher (bare `httpx.get`) and remain open.
- Replay to staging was blocked by a staging agent-claim sign-in loop
  (bookshelf-platform PR #285); the bundle is valid and ready to replay once a
  write token is available.
