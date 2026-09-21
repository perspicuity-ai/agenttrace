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
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

FORMAT_CADDY = "caddy"
FORMAT_COMBINED = "combined"
FORMATS = (FORMAT_CADDY, FORMAT_COMBINED)

#: The common/combined shape. The leading host fields are 3 (common/combined) or 4
#: (a vhost-prefixed log); the trailing quoted fields are 0, 1 or 2. One quoted field is
#: ambiguous in the wild — Apache's stock ``referer`` format puts a referer there and its
#: ``agent`` format puts a user-agent there — so it is read as a user-agent only when it
#: does not look like a URL. See ``docs/DESIGN.md``, D12.
_COMBINED_RE = re.compile(
    r"^(?:\S+[ \t]+){3,4}"
    r"\[(?P<time>[^\]]+)\][ \t]+"
    r'"(?P<request>[^"]*)"[ \t]+'
    r"(?P<status>[0-9]{3})[ \t]+"
    r"(?P<size>\S+)"
    r'(?:[ \t]+"(?P<quoted1>[^"]*)")?'
    r'(?:[ \t]+"(?P<quoted2>[^"]*)")?'
    r"[ \t]*$"
)

_URL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")

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
    """Read a status code, refusing anything that is not one.

    ``0`` is accepted as a recorded fact — Caddy writes it when no response was sent —
    and every report that acts on a status treats it as "no response", never as success.
    Anything outside 0 or 100–599 is not a status at all, so the line is not read.
    """

    if isinstance(value, bool):
        return None
    number: int | None = None
    if isinstance(value, int):
        number = value
    elif isinstance(value, float) and value.is_integer():
        number = int(value)
    elif isinstance(value, str) and value.strip().isdigit():
        number = int(value.strip())
    if number is None:
        return None
    if number == 0 or 100 <= number <= 599:
        return number
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
    if len(parts) < 2:
        # A target with no path is not a request this tool can describe. Inventing "/"
        # would report a page the server never logged.
        return None
    method = parts[0].upper()
    uri = parts[1]
    agent = _trailing_user_agent(match.group("quoted1"), match.group("quoted2"))
    return Entry(
        timestamp=moment,
        method=method,
        path=path_of(uri),
        status=status,
        user_agent=agent,
    )


def _trailing_user_agent(first: str | None, second: str | None) -> str:
    """Decide which trailing quoted field is the user-agent.

    Two fields are the combined format: referer, then user-agent. One field is
    ambiguous — Apache's stock ``referer`` format and its ``agent`` format both produce
    one — so it is read as a user-agent only when it does not look like a URL or a
    placeholder. The cost of guessing wrong is a client counted as unreadable rather than
    a referer misread as a client, which is the safer direction.
    """

    if second is not None:
        return second if second and second != "-" else ""
    if first is None or first in ("", "-"):
        return ""
    if _URL_RE.match(first.strip()):
        return ""
    return first


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

    return sniff(lines).fmt


#: A source with at least this share of unreadable lines, and at least this many of them,
#: gets a warning at the top of the report instead of a quiet number.
DRIFT_WARN_SHARE = 0.2
DRIFT_WARN_MIN_LINES = 3


@dataclass
class Sniffing:
    """What the first lines of a source looked like, kept so the report can explain itself."""

    fmt: str | None = None
    caddy_access_lines: int = 0
    combined_lines: int = 0
    json_objects: int = 0
    json_keys: Counter = field(default_factory=Counter)
    request_keys: Counter = field(default_factory=Counter)
    samples: list[str] = field(default_factory=list)

    @property
    def saw_json(self) -> bool:
        return self.json_objects > 0

    @property
    def undecided(self) -> bool:
        return self.fmt is None


def sniff(lines: list[str]) -> Sniffing:
    """Read the shape of a source's first lines: the format and the evidence for it."""

    result = Sniffing()
    for line in lines:
        text = line.strip()
        if not text:
            continue
        if text.startswith("{"):
            try:
                record = json.loads(text)
            except ValueError:
                record = None
            if isinstance(record, dict):
                result.json_objects += 1
                result.json_keys.update(record.keys())
                request = record.get("request")
                if isinstance(request, dict):
                    result.request_keys.update(request.keys())
            if parse_caddy_line(text) is not None:
                result.caddy_access_lines += 1
            elif len(result.samples) < 3:
                result.samples.append(_sample(text))
        elif _COMBINED_RE.match(text) is not None:
            result.combined_lines += 1
        elif len(result.samples) < 3:
            result.samples.append(_sample(text))
    if result.caddy_access_lines and result.caddy_access_lines >= result.combined_lines:
        result.fmt = FORMAT_CADDY
    elif result.combined_lines:
        result.fmt = FORMAT_COMBINED
    return result


def _sample(text: str, limit: int = 64) -> str:
    single = " ".join(text.split())
    return single if len(single) <= limit else single[: limit - 1] + "…"


def explain(sniffing: Sniffing) -> str:
    """A specific reason why the lines could not be read, in one sentence.

    "Nothing here is an access log" and "this is a JSON log whose fields have changed"
    are different findings, and a reader needs to be able to tell them apart.
    """

    if sniffing.saw_json and not sniffing.caddy_access_lines:
        keys = ", ".join(sorted(sniffing.json_keys)[:8]) or "none"
        detail = f"top-level keys seen: {keys}"
        if sniffing.request_keys:
            request_keys = ", ".join(sorted(sniffing.request_keys)[:8])
            detail += f"; keys inside request: {request_keys}"
            detail += "; expected request.uri and request.method"
        else:
            detail += "; expected a request object carrying uri and method"
        return (
            "these lines are JSON objects, but none carried the fields a Caddy access line "
            f"has (ts, status, {detail})"
        )
    if sniffing.samples:
        shown = " | ".join(sniffing.samples)
        return (
            "no line matched the Caddy JSON shape or the common/combined pattern; the first "
            f"lines that did not read were: {shown}"
        )
    return "no non-blank line was found at all"
