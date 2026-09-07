# PRIMAP-hist

National historical greenhouse gas emissions for every country and Kyoto gas from 1750,
combining country reported inventories with third party data to fill the gaps.

This repository contains the code to generate the PRIMAP-hist book
for the [bookshelf](https://github.com/climate-resource/bookshelf).

## Getting started

Install the local virtual environment:

```bash
   make virtual-environment
```

## Updating from the template

```bash
   copier update
```

The template declares no Copier tasks, so this works without `--trust`
and Renovate can propose template updates on its own.

Each dataset consists of two files:

- `bookshelf.yaml` is the recipe for the metadata about the dataset.
  `volume:` names the collection and its search vocabulary,
  `defaults:` holds what every book shares,
  and `books:` lists one entry per upstream version of the dataset.
- `build.py` is a standalone Jupytext build file holding only the processing.
  It calls `bookshelf.setup()` once, reads each declared input through `build.use(...)`,
  and writes its outputs with `build.book.write(..., used=[...])`.

### Recording a book

A bundle holds one book, so a version selects both what is recorded and where it lands:

```bash
   make run VERSION=v2.7
```

That records and validates `bundle/v2.7` without any API credentials.
Replay it to the Bookshelf API with `make publish VERSION=v2.7`,
and see which edition it would resolve to first with `make publish-dry-run VERSION=v2.7`.

Both targets and the CI workflows call the `bookshelf` CLI directly,
so this repository carries no publishing scripts of its own.
The same commands are available by hand:

```bash
   uv run bookshelf record --force --version v2.7 --bundle bundle/v2.7
   uv run bookshelf validate bundle/v2.7
   uv run bookshelf publish bundle/v2.7 --dry-run
```

Each takes `--json` for a machine readable summary, and carries its meaning in the exit code.

CI records every version `books:` declares, and the publish workflow replays every one of them.
Publishing an unchanged book is idempotent, so a version that has not moved keeps its edition.

### Worked examples

The SDK's [examples README](https://github.com/climate-resource/bookshelf/blob/main/examples/README.md)
lists the example feedstocks and explains how to use them.
The [recipe format](https://github.com/climate-resource/bookshelf/blob/main/docs/explanation/recipe-format.md)
documents every field.

## Publishing

Publishing uses the repository environment named `deploy`.
Configure `BOOKSHELF_CLIENT_ID` and `BOOKSHELF_CLIENT_SECRET` as environment secrets on that environment.
Set the public `BOOKSHELF_TOKEN_URL` repository variable to the WorkOS AuthKit token endpoint.
The generated publish caller uses `secrets: inherit`.
The reusable publish job carries `environment: deploy`, so those environment secrets are resolved when that job starts.

A first publish into a new volume needs that volume to exist.
`bookshelf publish` will not create one, so it fails with `Series 'primap-hist' not found`.
Create it once, from an account with WRITE:

```bash
   uv run bookshelf volume create primap-hist --licence CC-BY-4.0
```

`visibility` in `bookshelf.yaml` sets the tier of the book and of everything the build records,
the `build.ipynb` and `build.html` documents included.
Pass `visibility=` on a single `build.book.write(...)` call to narrow that one resource,
so a public book can still hold a member only your organisation may read.

The recorded bundle also carries the executed script and notebook, so its bundle hash covers the build source.
Any edit to `build.py`, a comment included, produces a new bundle hash.
Publishing after a source-only edit therefore creates a new edition whose data is unchanged.
The underlying resources are deduplicated if they don't change.

## Releasing

Dispatch the "Bump version" workflow and pick a bump rule.
It bumps the version with `uv version`, builds the CHANGELOG with towncrier, tags,
and drafts the GitHub release, all in one run.

Publishing that draft release by hand is what triggers the publish workflow.
A release published by CI would not fire it,
because releases created with `GITHUB_TOKEN` do not trigger other workflows.
