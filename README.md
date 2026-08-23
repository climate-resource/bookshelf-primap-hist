# PRIMAP-hist

PRIMAP-hist national historical emissions time series

This repository contains the code to generate the PRIMAP-hist book
for the [bookshelf](https://github.com/climate-resource/bookshelf).

## Getting started

Install the local virtual environment:

```bash
   make virtual-environment
```

The recipe is in `bookshelf.yaml`.
It declares the volume, the metadata every book shares under `defaults:`,
and one entry under `books:` for each published PRIMAP-hist version.
Each book states only what differs: its licence, DOI, release date, release notes
and the raw Zenodo CSV it is built from.
The source code that builds a book is in `build.py`.
It holds the processing and nothing else, because the facts live in the recipe.

A book is recorded with `make run`, which defaults to the newest version.
Pick another with `make run VERSION=v2.6`.
This creates a validated local bundle in `bundle/` without API credentials.
Each version is recorded and published in its own run, because a bundle holds one book.

The bundle can be replayed to the Bookshelf API using `make publish`.
The publish workflow normally performs that step on a release.
Run `make publish-dry-run` first to see which edition the bundle resolves to without publishing.

Both targets and the CI workflows call the `bookshelf` CLI directly,
so this repository carries no publishing scripts of its own.
The same three commands are available by hand:

```bash
   uv run bookshelf record --force --version v2.7
   uv run bookshelf validate
   uv run bookshelf publish --dry-run
```

Each takes `--json` for a machine readable summary, and carries its meaning in the exit code.
`record` without `--version` exits non-zero and lists the versions the recipe declares.

Publishing uses the repository environment named `deploy`.
Configure `BOOKSHELF_CLIENT_ID` and `BOOKSHELF_CLIENT_SECRET` as environment secrets on that environment.
Set the public `BOOKSHELF_TOKEN_URL` repository variable to the WorkOS AuthKit token endpoint.
The generated publish caller uses `secrets: inherit`.
The reusable publish job carries `environment: deploy`, so those environment secrets are resolved when that job starts.

`visibility` under `defaults:` sets the tier of every book and of everything the build records,
the `build.ipynb` and `build.html` documents included.
A single book may override it, and a single `book.write(...)` call may pass `visibility=` to narrow one resource.

Identical inputs must create identical data bytes and stable lineage identifiers.

Adding a new data version means adding an entry under `books:` with its DOI, release date,
a short description of what changed, and the URL and sha256 of the raw CSV.
Zenodo publishes md5 only, so the sha256 has to be taken from the downloaded file.

The recorded bundle also carries the executed script/notebook, so its bundle hash covers the build source.
Any edit to `build.py`, a comment included, produces a new bundle hash.
Publishing after a source-only edit therefore creates a new edition whose data is unchanged.
The underlying resources are deduplicated if they don't change.

## Testing

`make test` checks that the recipe loads and that every book resolves to the expected metadata.
The record tests fetch each raw CSV from Zenodo and run `bookshelf record` and `validate` for every version,
so they are skipped by default.
Run them with `uv run pytest -m record`.

## Releasing

Dispatch the "Bump version" workflow and pick a bump rule.
It bumps the version with `uv version`, builds the CHANGELOG with towncrier, tags,
and drafts the GitHub release, all in one run.

Publishing that draft release by hand is what triggers the publish workflow.
A release published by CI would not fire it,
because releases created with `GITHUB_TOKEN` do not trigger other workflows.
