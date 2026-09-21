# PRIMAP-hist

National historical greenhouse gas emissions for every country and Kyoto gas from 1750,
combining country reported inventories with third party data to fill the gaps.

This repository is a feedstock containing code that turns upstream data into books on the
[bookshelf](https://github.com/climate-resource/bookshelf).

The two key files for a bookshelf feedstock are:

- `bookshelf.yaml` is the recipe declaring the metadata, versions and required versions.
- `build.py` is the script to process a given version of a dataset into data ready for the bookshelf.

## Getting started

Install the local virtual environment:

```bash
   make virtual-environment
```

Then build one version of the dataset:

```bash
   make run VERSION=v2.7
```

`VERSION` picks one entry from `books:` in the recipe.
The result lands in `bundle/v2.7` and is then validated.
This does not upload the result, but can be inspected locally.

## Publishing

Each pull request builds a preview for each version declared in `bookshelf.yaml`.
A URL to review the diff between the published versions and the built version are commented to the pull request.
Merging publishes that preview to the bookshelf.

Everything else about this feedstock lives in the README of
[copier-bookshelf-dataset](https://github.com/climate-resource/copier-bookshelf-dataset).
