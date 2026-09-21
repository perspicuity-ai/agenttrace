"""Read access-log lines into one record type, from two formats.

Two shapes are supported, because they are the two a host is likely to have:

``caddy``
    One JSON object per line, as Caddy writes it: ``ts``, ``status``, and a
    ``request`` object carrying ``uri``, ``method`` and ``headers.User-Agent``.

``combined``
    The common/combined format most other servers write:
    ``host ident user [time] "request" status bytes "referer" "user-agent"``.
    The user-agent and referer fields are optional, so the common format parses too.

The client address is the first field of a combined line and ``remote_ip`` of a Caddy
line. Neither is ever extracted: the reader does not need an address to answer any of
its questions, and a value that is never read cannot leak into the output later.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

FORMAT_CADDY = "caddy"
FORMAT_COMBINED = "combined"
FORMATS = (FORMAT_CADDY, FORMAT_COMBINED)

_COMBINED_RE = re.compile(
    r"^(?P<host>\S+)[ \t]+(?P<ident>\S+)[ \t]+(?P<user>\S+)[ \t]+"
    r"\[(?P<time>[^\]]+)\][ \t]+"
    r'"(?P<request>[^"]*)"[ \t]+'
    r"(?P<status>[0-9]{3})[ \t]+"
    r"(?P<size>\S+)"
    r'(?:[ \t]+"(?P<referer>[^"]*)"[ \t]+"(?P<agent>[^"]*)")?'
    r"[ \t]*$"
)

_TS_RE = re.compile(
    r"^(?P<day>[0-9]{1,2})/(?P<month>[A-Za-z]{3})/(?P<year>[0-9]{4})"
    r":(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    r"(?:[ \t]+(?P<sign>[+-])(?P<tzhour>[0-9]{2})(?P<tzminute>[0-9]{2}))?$"
)

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_ABSOLUTE_URI_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://[^/?#]*(?P<path>/[^?#]*)?")


@dataclass(frozen=True)
class Entry:
    """One request, with everything the report needs and nothing else."""

    timestamp: datetime
    method: str
    path: str
    status: int
    user_agent: str


def path_of(uri: str) -> str:
    """Return the request path: query string and fragment removed.

    Unique-path counts and the "asked for and did not get" list would otherwise
    fragment over tracking parameters and per-request noise: a 404 for ``/x?a=1`` and
    a 404 for ``/x`` are one missing page.
    """

    value = (uri or "").strip()
    if not value:
        return "/"
    match = _ABSOLUTE_URI_RE.match(value)
    if match:
        value = match.group("path") or "/"
    value = value.split("#", 1)[0].split("?", 1)[0]
    return value or "/"


def _utc_from_epoch(value: object) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _utc_from_string(value: str) -> datetime | None:
    text = value.strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def timestamp_of(value: object) -> datetime | None:
    """Read a Caddy ``ts`` (epoch seconds, or an ISO string when configured so)."""

    if isinstance(value, str):
        return _utc_from_string(value)
    return _utc_from_epoch(value)


def combined_timestamp(value: str) -> datetime | None:
    """Read ``10/Oct/2000:13:55:36 -0700`` without depending on the C locale."""

    match = _TS_RE.match(value.strip())
    if not match:
        return None
    month = _MONTHS.get(match.group("month").lower())
    if month is None:
        return None
    offset = timedelta(0)
    if match.group("sign"):
        hours = int(match.group("tzhour"))
        minutes = int(match.group("tzminute"))
        offset = timedelta(hours=hours, minutes=minutes)
        if match.group("sign") == "-":
            offset = -offset
    try:
        moment = datetime(
            int(match.group("year")), month, int(match.group("day")),
            int(match.group("hour")), int(match.group("minute")), int(match.group("second")),
            tzinfo=timezone(offset),
        )
    except ValueError:
        return None
    return moment.astimezone(timezone.utc)


def _status_of(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _header(headers: object, name: str) -> str:
    """Read a header case-insensitively; Caddy logs the values as a list."""

    if not isinstance(headers, dict):
        return ""
    wanted = name.lower()
    for key, value in headers.items():
        if isinstance(key, str) and key.lower() == wanted:
            if isinstance(value, list):
                return str(value[0]) if value else ""
            if value is None:
                return ""
            return str(value)
    return ""


def parse_caddy_line(line: str) -> Entry | None:
    """Parse one Caddy JSON access line, or return ``None``."""

    if not line.startswith("{"):
        return None
    try:
        record = json.loads(line)
    except ValueError:
        return None
    if not isinstance(record, dict):
        return None
    request = record.get("request")
    if not isinstance(request, dict):
        return None
    moment = timestamp_of(record.get("ts"))
    status = _status_of(record.get("status"))
    uri = request.get("uri")
    if moment is None or status is None or not isinstance(uri, str):
        return None
    method = request.get("method")
    return Entry(
        timestamp=moment,
        method=str(method).upper() if isinstance(method, str) and method else "?",
        path=path_of(uri),
        status=status,
        user_agent=_header(request.get("headers"), "User-Agent"),
    )


def parse_combined_line(line: str) -> Entry | None:
    """Parse one common/combined line, or return ``None``."""

    match = _COMBINED_RE.match(line.strip())
    if not match:
        return None
    moment = combined_timestamp(match.group("time"))
    status = _status_of(match.group("status"))
    if moment is None or status is None:
        return None
    request = match.group("request").strip()
    if not request or request == "-":
        return None
    parts = request.split()
    method = parts[0].upper() if parts else "?"
    uri = parts[1] if len(parts) > 1 else "/"
    agent = match.group("agent")
    return Entry(
        timestamp=moment,
        method=method,
        path=path_of(uri),
        status=status,
        user_agent=agent if agent and agent != "-" else "",
    )


def parse_line(line: str, fmt: str | None = None) -> tuple[Entry | None, str | None]:
    """Parse *line*, optionally pinned to *fmt*.

    Returns the entry and the format that produced it, so a caller can count lines
    that no parser could read.
    """

    text = line.rstrip("\n")
    if not text.strip():
        return None, None
    if fmt == FORMAT_CADDY:
        return parse_caddy_line(text), FORMAT_CADDY
    if fmt == FORMAT_COMBINED:
        return parse_combined_line(text), FORMAT_COMBINED
    if text.lstrip().startswith("{"):
        entry = parse_caddy_line(text)
        if entry is not None:
            return entry, FORMAT_CADDY
    entry = parse_combined_line(text)
    if entry is not None:
        return entry, FORMAT_COMBINED
    return None, None


def sniff_format(lines: list[str]) -> str | None:
    """Decide a source's format from its own lines, or ``None`` if undecided.

    A file is assumed to be one format; the ``--format`` flag overrides this when a
    file is damaged or mixed.
    """

    caddy = combined = 0
    for line in lines:
        text = line.strip()
        if not text:
            continue
        if text.startswith("{"):
            if parse_caddy_line(text) is not None:
                caddy += 1
        elif _COMBINED_RE.match(text) is not None:
            combined += 1
    if caddy and caddy >= combined:
        return FORMAT_CADDY
    if combined:
        return FORMAT_COMBINED
    return None
