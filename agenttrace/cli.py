"""Command line: `python3 -m agenttrace [options] <log> [<log> ...]`.

Input is a file, several files, a glob, or standard input. Output is a text report,
or a JSON document with `--json`. Nothing is captured and nothing is fetched: the
tool reads what the web server already wrote.

Exit codes, so a script can tell the three outcomes apart:

* ``0`` — a report was produced. Zero claimed agents is still a report.
* ``1`` — a usage or input error: no input named, a path that does not exist, a
  directory instead of a file, an unreadable file. The reason goes to stderr.
* ``2`` — the input could be opened but nothing in it was recognisable as an access
  log line, so no report exists to give. This is the "the server may not be logging
  at all" case, and it is not the same answer as "no agents came".
"""

from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import Iterator, TextIO

from . import TOOL_NAME, __version__
from .classify import classify
from .parse import FORMATS, parse_line, sniff_format
from .report import (
    STATE_NO_READABLE_LINES,
    Analysis,
    Source,
    render_json_text,
    render_text,
)

#: How many lines are read before the format is decided for a source.
SNIFF_LINES = 200

_GLOB_CHARS = set("*?[")


class InputError(Exception):
    """A problem with the input that the caller can fix."""


class _Parser(argparse.ArgumentParser):
    """Argparse exits 2 on a usage error; here 2 means "nothing readable"."""

    def error(self, message: str) -> None:  # pragma: no cover - argparse plumbing
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog=TOOL_NAME,
        description=(
            "Report what claimed AI agents asked a web server for, from an access log "
            "that already exists. Counts are of self-declared user-agent strings."
        ),
        epilog=(
            "A user-agent string is spoofable, so the report counts claims, not verified "
            "agents. No client address is read or printed."
        ),
    )
    parser.add_argument(
        "logs",
        nargs="*",
        metavar="LOG",
        help="an access log file, several files, a glob, or - for standard input",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="read an access log from standard input",
    )
    parser.add_argument(
        "--format",
        choices=FORMATS,
        default=None,
        help="override format detection (caddy JSON or common/combined)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="print a JSON document instead of the text report",
    )
    parser.add_argument("--version", action="version", version=f"{TOOL_NAME} {__version__}")
    return parser


def expand_targets(arguments: list[str]) -> list[tuple[str, str]]:
    """Resolve the positional arguments to ``(kind, name)`` targets, in order.

    ``kind`` is ``file`` or ``stdin``. Duplicates are dropped so that naming a file
    twice does not count its requests twice.
    """

    targets: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(kind: str, name: str, key: str) -> None:
        if key not in seen:
            seen.add(key)
            targets.append((kind, name))

    for argument in arguments:
        if argument == "-":
            add("stdin", "<stdin>", "stdin")
            continue
        if _GLOB_CHARS & set(argument):
            matches = sorted(glob.glob(argument, recursive=True))
            if not matches:
                raise InputError(f"no files match {argument!r}")
            for match in matches:
                if os.path.isdir(match):
                    raise InputError(
                        f"{match!r} is a directory; name log files or a glob that matches "
                        f"files only"
                    )
                add("file", match, os.path.abspath(match))
            continue
        if not os.path.exists(argument):
            raise InputError(f"no such file: {argument!r}")
        if os.path.isdir(argument):
            raise InputError(
                f"{argument!r} is a directory; name the log files or use a glob such as "
                f"{argument.rstrip('/')}/*.log"
            )
        add("file", argument, os.path.abspath(argument))
    return targets


def iter_lines(stream: TextIO) -> Iterator[str]:
    for raw in stream:
        yield raw.rstrip("\n").rstrip("\r")


def analyse_stream(
    name: str, stream: TextIO, forced_format: str | None, analysis: Analysis
) -> Source:
    """Read one source into *analysis*, deciding its format from its own lines."""

    source = Source(name=name, fmt=forced_format)
    lines = iter_lines(stream)

    sample: list[str] = []
    for line in lines:
        sample.append(line)
        if len(sample) >= SNIFF_LINES:
            break
    fmt = forced_format or sniff_format(sample)
    source.fmt = fmt

    def handle(line: str) -> None:
        source.lines_read += 1
        if not line.strip():
            return
        entry, _used = parse_line(line, fmt)
        if entry is None:
            source.lines_not_requests += 1
            return
        source.requests_read += 1
        analysis.add(entry, classify(entry.user_agent))

    for line in sample:
        handle(line)
    for line in lines:
        handle(line)

    analysis.add_source(source)
    return source


def run(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.logs and not args.stdin:
        parser.error(
            "no input: name an access log (a path, several paths or a glob), or use --stdin"
        )

    try:
        targets = expand_targets(args.logs)
    except InputError as error:
        print(f"{TOOL_NAME}: {error}", file=sys.stderr)
        print(f"{TOOL_NAME}: no report produced.", file=sys.stderr)
        return 1
    if args.stdin:
        targets.insert(0, ("stdin", "<stdin>"))

    analysis = Analysis()
    for kind, name in targets:
        try:
            if kind == "stdin":
                analyse_stream(name, sys.stdin, args.format, analysis)
            else:
                with open(name, "r", encoding="utf-8", errors="replace") as stream:
                    analyse_stream(name, stream, args.format, analysis)
        except OSError as error:
            print(f"{TOOL_NAME}: cannot read {name}: {error.strerror or error}", file=sys.stderr)
            print(f"{TOOL_NAME}: no report produced.", file=sys.stderr)
            return 1

    output = render_json_text(analysis) if args.as_json else render_text(analysis) + "\n"
    try:
        sys.stdout.write(output)
        sys.stdout.flush()
    except BrokenPipeError:  # the reader closed the pipe, e.g. `| head`
        try:
            sys.stdout.close()
        finally:
            return 0
    return 2 if analysis.state == STATE_NO_READABLE_LINES else 0


def main(argv: list[str] | None = None) -> int:
    return run(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
