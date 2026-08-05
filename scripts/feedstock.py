"""
Record and publish the PRIMAP-hist feedstock.

Uses the SDK to build and publish the book
"""

import argparse
import json
import sys
from pathlib import Path

from bookshelf import Bookshelf
from bookshelf.publisher import parse_parameters, replay_bundle_sync, run_record

ROOT = Path(__file__).parent.parent


def record(args: argparse.Namespace) -> None:
    """Execute the build file named by the recipe and print the bundle summary."""
    summary = run_record(
        build_path=None,
        recipe_path=args.recipe,
        bundle_path=args.bundle,
        parameters=parse_parameters(args.parameter),
        cwd=ROOT,
    )
    print(json.dumps(summary, indent=2))


def publish(args: argparse.Namespace) -> None:
    """Replay the bundle and print the resulting book coordinate."""
    with Bookshelf(args.base_url) as bs:
        book = replay_bundle_sync(args.bundle, bs)
    detail = book.metadata
    coordinate = f"{detail.version}_e{detail.edition:03}"
    print(f"{detail.series_name} {coordinate} ({detail.status})")


def main(argv: list[str] | None = None) -> int:
    """Dispatch to the requested subcommand."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--bundle", type=Path, default=ROOT / "bundle")

    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(required=True)

    recorder = subcommands.add_parser(
        "record",
        parents=[common],
        help="execute the build file into a reviewable bundle",
    )
    recorder.add_argument("--recipe", type=Path, default=ROOT / "bookshelf.yaml")
    recorder.add_argument(
        "-p",
        "--parameter",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="override a build parameter, parsed as a YAML scalar",
    )
    recorder.set_defaults(func=record)

    publisher = subcommands.add_parser(
        "publish",
        parents=[common],
        help="replay the recorded bundle to the API, needs a write token",
    )
    publisher.add_argument(
        "--base-url",
        default=None,
        help="Bookshelf API base URL, defaults to the SDK's configured value",
    )
    publisher.set_defaults(func=publish)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
