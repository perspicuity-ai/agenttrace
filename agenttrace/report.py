"""Aggregate parsed requests and render the report.

Two renderings of the same analysis: a text report for a person and a JSON document
for a script. Both carry the claim boundary, and neither can carry a client address —
the analysis only ever sees the fields :class:`agenttrace.parse.Entry` holds.

Three honesty rules shape the report beyond the counts:

* a client the operator declared as their own (``--self``) is set aside and never
  presented as an agent or a bot claim;
* when one undeclared client dominates the log, the report says so by name and says
  that the tool cannot tell whether it is the site's own monitoring;
* user-agent strings that matched no rule are shown with their counts, so
  "unrecognised" is a starting point for a reader rather than a dead end.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from . import CLAIM_BOUNDARY, DISCOVERY_FILES, NO_LOG_HOST, TOOL_NAME, __version__
from .classify import (
    CATEGORY_LABELS,
    CATEGORY_NAMED_AGENT,
    CATEGORY_ORDER,
    CATEGORY_SEARCH_CRAWLER,
    CATEGORY_SELF,
    CATEGORY_UNKNOWN,
    NAMED_AI_AGENTS,
    Claim,
)
from .parse import Entry

STATE_REPORTED = "reported"
STATE_NO_AGENT_TRAFFIC = "no_agent_traffic"
STATE_NO_READABLE_LINES = "no_readable_lines"

TOP_PATHS = 10
TOP_CLIENTS = 5

#: A window shorter than this gets a sentence saying the counts describe that window only.
SHORT_WINDOW_SECONDS = 3600

#: How much of a log one undeclared client must hold before the report calls it out.
DOMINANCE_SHARE = 0.5
DOMINANCE_MIN_REQUESTS = 5

_CONTROL = re.compile(r"[\x00-\x1f\x7f]|\x1b\[[0-9;]*[A-Za-z]")


def safe_client(text: str, limit: int = 60) -> str:
    """Make a self-declared user-agent string safe to echo.

    A user-agent is attacker-controlled text that lands in a terminal. Control
    characters, escape sequences and newlines are removed, whitespace is collapsed, and
    the result is truncated — the report shows what was claimed, not what it can do.
    """

    cleaned = _CONTROL.sub("", text or "")
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > limit:
        return cleaned[: limit - 1] + "…"
    return cleaned or "(no user-agent)"


@dataclass
class Source:
    """What was read from one file, or from standard input."""

    name: str
    fmt: str | None
    lines_read: int = 0
    requests_read: int = 0
    lines_not_requests: int = 0
    #: Plain sentences about lines this source could not read, and why.
    diagnostics: list[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return self.fmt or "undecided"

    @property
    def unreadable_share(self) -> float:
        return self.lines_not_requests / self.lines_read if self.lines_read else 0.0


@dataclass
class AgentRecord:
    """One label: a named AI agent, a named search crawler, a category, or a declaration."""

    label: str
    category: str
    requests: int = 0
    paths: set[str] = field(default_factory=set)
    first: datetime | None = None
    last: datetime | None = None
    statuses: Counter = field(default_factory=Counter)
    discovery: dict[str, Counter] = field(default_factory=dict)

    @property
    def unique_paths(self) -> int:
        return len(self.paths)

    def observe(self, entry: Entry) -> None:
        self.requests += 1
        self.paths.add(entry.path)
        self.statuses[entry.status] += 1
        if self.first is None or entry.timestamp < self.first:
            self.first = entry.timestamp
        if self.last is None or entry.timestamp > self.last:
            self.last = entry.timestamp


@dataclass
class MissingPath:
    path: str
    requests: int = 0
    statuses: Counter = field(default_factory=Counter)
    agents: set[str] = field(default_factory=set)


@dataclass
class DominantClient:
    """An undeclared client holding most of the log."""

    user_agent: str
    requests: int
    category: str

    def share(self, total: int) -> float:
        return self.requests / total if total else 0.0


class Analysis:
    """Everything the report needs, accumulated in one pass."""

    def __init__(self, declarations: tuple[str, ...] = ()) -> None:
        self.declarations = tuple(declarations)
        self.sources: list[Source] = []
        self.requests = 0
        self.by_category: Counter = Counter()
        #: Keyed by (category, label) so a declaration named like an agent cannot merge
        #: with that agent's record.
        self.by_label: dict[tuple[str, str], AgentRecord] = {}
        self.statuses: Counter = Counter()
        self.agent_paths: Counter = Counter()
        self.missing: dict[str, MissingPath] = {}
        self.clients: Counter = Counter()
        self.client_categories: dict[str, str] = {}
        self.unrecognised: Counter = Counter()
        self.discovery: dict[str, dict] = {
            path: {"requests": 0, "agents": set(), "statuses": Counter()}
            for path in DISCOVERY_FILES
        }
        self.first: datetime | None = None
        self.last: datetime | None = None

    # -- accumulation ---------------------------------------------------------

    def add_source(self, source: Source) -> None:
        self.sources.append(source)

    def add(self, entry: Entry, claim: Claim) -> None:
        self.requests += 1
        self.by_category[claim.category] += 1
        self.statuses[entry.status] += 1
        client = safe_client(entry.user_agent)
        self.clients[client] += 1
        self.client_categories.setdefault(client, claim.category)
        if claim.category == CATEGORY_UNKNOWN:
            self.unrecognised[client] += 1
        if self.first is None or entry.timestamp < self.first:
            self.first = entry.timestamp
        if self.last is None or entry.timestamp > self.last:
            self.last = entry.timestamp

        key = (claim.category, claim.label)
        record = self.by_label.get(key)
        if record is None:
            record = AgentRecord(label=claim.label, category=claim.category)
            self.by_label[key] = record
        record.observe(entry)

        if entry.path.lower() in DISCOVERY_FILES:
            seen = self.discovery[entry.path.lower()]
            seen["requests"] += 1
            seen["statuses"][entry.status] += 1
            if claim.is_named_agent:
                seen["agents"].add(claim.label)
                record.discovery.setdefault(entry.path.lower(), Counter())[entry.status] += 1

        if claim.is_named_agent:
            self.agent_paths[entry.path] += 1
            if entry.status in (404, 410):
                missing = self.missing.get(entry.path)
                if missing is None:
                    missing = MissingPath(path=entry.path)
                    self.missing[entry.path] = missing
                missing.requests += 1
                missing.statuses[entry.status] += 1
                missing.agents.add(claim.label)

    # -- derived --------------------------------------------------------------

    @property
    def named_agents(self) -> list[AgentRecord]:
        return self._records(CATEGORY_NAMED_AGENT)

    @property
    def search_crawlers(self) -> list[AgentRecord]:
        return self._records(CATEGORY_SEARCH_CRAWLER)

    @property
    def declared_self(self) -> list[AgentRecord]:
        return self._records(CATEGORY_SELF)

    def unmatched_declarations(self) -> list[str]:
        matched = {record.label for record in self.declared_self}
        return [token for token in self.declarations if token not in matched]

    def _records(self, category: str) -> list[AgentRecord]:
        rows = [r for r in self.by_label.values() if r.category == category]
        return sorted(rows, key=lambda r: (-r.requests, r.label.lower()))

    def record_for(self, label: str, category: str) -> AgentRecord | None:
        return self.by_label.get((category, label))

    @property
    def named_agent_requests(self) -> int:
        return self.by_category[CATEGORY_NAMED_AGENT]

    @property
    def agent_share(self) -> float:
        return self.named_agent_requests / self.requests if self.requests else 0.0

    @property
    def coverage_seconds(self) -> float | None:
        if self.first is None or self.last is None:
            return None
        return (self.last - self.first).total_seconds()

    @property
    def unknown_clients(self) -> list[tuple[str, int]]:
        """The user-agent strings that matched no rule, most requests first."""

        return self.unrecognised.most_common(TOP_CLIENTS)

    @property
    def dominant_client(self) -> DominantClient | None:
        """The busiest client that is neither a named agent nor declared as the site's own."""

        if self.requests < DOMINANCE_MIN_REQUESTS:
            return None
        for client, count in self.clients.most_common():
            category = self.client_categories.get(client, CATEGORY_UNKNOWN)
            if category in (CATEGORY_NAMED_AGENT, CATEGORY_SELF):
                continue
            if count / self.requests < DOMINANCE_SHARE:
                return None
            return DominantClient(user_agent=client, requests=count, category=category)
        return None

    @property
    def state(self) -> str:
        if self.requests == 0:
            return STATE_NO_READABLE_LINES
        if self.named_agent_requests == 0:
            return STATE_NO_AGENT_TRAFFIC
        return STATE_REPORTED

    def status_mix(self, statuses: Counter) -> str:
        parts = [f"{code}:{count}" for code, count in sorted(
            statuses.items(), key=lambda item: (-item[1], item[0]))]
        return " ".join(parts) if parts else "-"


def _iso(moment: datetime | None) -> str | None:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ") if moment else None


def _percent(part: int, whole: int) -> str:
    if not whole:
        return "0.0%"
    return f"{100.0 * part / whole:.1f}%"


def _duration(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    if seconds < 120:
        return f"{int(seconds)} seconds"
    if seconds < 7200:
        return f"{seconds / 60:.1f} minutes"
    if seconds < 172800:
        return f"{seconds / 3600:.1f} hours"
    return f"{seconds / 86400:.1f} days"


def _mix(statuses: Counter) -> str:
    return " ".join(f"{code}:{count}" for code, count in sorted(
        statuses.items(), key=lambda item: (-item[1], item[0])))


# -- text rendering -----------------------------------------------------------


def render_text(analysis: Analysis) -> str:
    lines: list[str] = []
    add = lines.append

    add(f"{TOOL_NAME} — what claimed AI agents asked a web server for")
    add("")
    for source in analysis.sources:
        add(
            f"source  {source.name}  ({source.label})  "
            f"{source.lines_read} lines, {source.requests_read} read as requests, "
            f"{source.lines_not_requests} not read as requests"
        )
    if analysis.first and analysis.last:
        add(
            f"coverage  {_iso(analysis.first)} .. {_iso(analysis.last)}  "
            f"({_duration(analysis.coverage_seconds)}, {analysis.requests} requests)"
        )
    add("")

    if analysis.state == STATE_NO_READABLE_LINES:
        lines.extend(_wrap(CLAIM_BOUNDARY))
        add("")
        return "\n".join(lines + _source_warnings(analysis) + _no_readable_lines(analysis))

    lines.extend(_wrap(CLAIM_BOUNDARY))
    add("")
    lines.extend(_source_warnings(analysis))
    lines.extend(_dominance_note(analysis))
    if analysis.state == STATE_NO_AGENT_TRAFFIC:
        return "\n".join(lines + _no_agent_traffic(analysis))

    add("Is /llms.txt being read?")
    add("")
    add(f"  VERDICT: {_discovery_line(analysis, DISCOVERY_FILES[0])}")
    add("")
    add("Discovery files requested by named AI agents")
    add("")
    for path in DISCOVERY_FILES:
        add(f"  {path:<13} {_discovery_line(analysis, path)}")
    add("")

    add(f"Named AI agents — {len(analysis.named_agents)} of 12 seen")
    add("")
    lines.extend(_agent_table(analysis.named_agents))
    not_seen = _not_seen(analysis)
    if not_seen:
        lines.extend(_wrap(f"  not seen in this log: {', '.join(not_seen)}", indent="  "))
    add("")

    if analysis.search_crawlers:
        add("Search crawlers seen")
        add("")
        lines.extend(_agent_table(analysis.search_crawlers))
        add("")

    if analysis.declared_self:
        add("Set aside — declared your own (--self)")
        add("")
        for record in analysis.declared_self:
            add(f"  {record.requests:>8}  {safe_client(record.label)}  "
                f"({record.unique_paths} path(s))")
        add("")
    unmatched = analysis.unmatched_declarations()
    if unmatched:
        lines.extend(_wrap(
            "  --self matched nothing for: "
            + ", ".join(safe_client(token) for token in unmatched)
            + " — check the spelling; a declaration that matches nothing sets nothing aside.",
            indent="  ",
        ))
        add("")

    unknown = analysis.unknown_clients
    if unknown:
        add(f"Unrecognised user agents (top {TOP_CLIENTS})")
        add("")
        for client, count in unknown:
            add(f"  {count:>8}  {client}")
        lines.extend(_wrap(
            "  These matched no rule and no --self declaration. Read them before drawing a "
            "conclusion from the counts above: a site's own monitor, a status checker or a "
            "client library lands here.",
            indent="  ",
        ))
        add("")

    add("Site-wide")
    add("")
    add(f"  requests in this log               {analysis.requests:>6}")
    for category in CATEGORY_ORDER:
        count = analysis.by_category[category]
        if category == CATEGORY_NAMED_AGENT:
            add(f"  claimed by a named AI agent        {count:>6}  ({_percent(count, analysis.requests)})")
        elif count or category != CATEGORY_SELF:
            add(f"  {CATEGORY_LABELS[category]:<33}{count:>6}  ({_percent(count, analysis.requests)})")
    add("")

    add(f"Top paths fetched by named AI agents (top {TOP_PATHS})")
    add("")
    if analysis.agent_paths:
        for path, count in analysis.agent_paths.most_common(TOP_PATHS):
            add(f"  {count:>4}  {path}")
        remaining = len(analysis.agent_paths) - min(TOP_PATHS, len(analysis.agent_paths))
        if remaining > 0:
            add(f"  ... {remaining} further distinct path(s) requested")
    else:
        add("  none")
    add("")

    add("Paths named AI agents asked for and did not get (404, 410)")
    add("")
    if analysis.missing:
        for item in sorted(analysis.missing.values(), key=lambda m: (-m.requests, m.path)):
            add(f"  {item.requests:>4}  {item.path}  "
                f"({_mix(item.statuses)}; {', '.join(sorted(item.agents))})")
    else:
        add("  none — every path a named AI agent asked for was served")
    add("")
    lines.extend(_wrap(
        "Only requests that reached this server and were written to this log are counted. "
        "Requests that never arrived are invisible, and a page being served is not evidence "
        "that it was read."
    ))
    return "\n".join(lines)


def _source_warnings(analysis: Analysis) -> list[str]:
    rows: list[str] = []
    for source in analysis.sources:
        for sentence in source.diagnostics:
            rows.extend(_wrap(f"  WARNING  {source.name}: {sentence}", indent="  "))
    if rows:
        rows.append("")
    return rows


def _dominance_note(analysis: Analysis) -> list[str]:
    """Nothing at all unless one undeclared client holds most of the log."""

    dominant = analysis.dominant_client
    if dominant is None:
        return []
    first_word = dominant.user_agent.split(" ")[0].split("/")[0]
    rows = [
        f"  {dominant.requests} of {analysis.requests} requests "
        f"({_percent(dominant.requests, analysis.requests)}) came from one client: "
        f"{dominant.user_agent}",
        "",
    ]
    rows.extend(_wrap(
        "  The tool cannot tell whether that is your own monitoring, a status checker or "
        "somebody else's bot. If it is yours, rerun with "
        f"--self {first_word} and its requests are set aside from the agent and bot counts; "
        "until then, read the totals below knowing that one client holds most of this log.",
        indent="  ",
    ))
    rows.append("")
    return rows


def discovery_verdict(statuses: Counter) -> tuple[str, bool]:
    """What a set of statuses says about whether the file was served.

    Below 400 is not "read": a 302 to a missing file is not the file, and a 0 means no
    response was recorded at all. Only 2xx counts as served; 304 counts as read because
    the client's copy was current, and it says so.
    """

    codes = set(statuses)
    if any(200 <= code < 300 for code in codes):
        return "READ", True
    if 304 in codes:
        return "READ (NOT MODIFIED — the client already held a copy)", True
    if any(300 <= code < 400 for code in codes):
        redirects = ", ".join(str(code) for code in sorted(c for c in codes if 300 <= c < 400))
        return f"REDIRECTED ({redirects}) — the file itself was not served at this path", False
    if 0 in codes:
        return "NO RESPONSE RECORDED — the request produced no status", False
    return "REQUESTED BUT NOT SERVED", False


def _named_agent_statuses(analysis: Analysis, path: str) -> dict[str, Counter]:
    return {
        name: _statuses_of(analysis, name, path)
        for name in sorted(analysis.discovery[path]["agents"])
    }


def _discovery_line(analysis: Analysis, path: str) -> str:
    """One sentence per discovery file: read, not requested, or requested and refused."""

    counts = _named_agent_statuses(analysis, path)
    if not counts:
        return "NOT REQUESTED — no named AI agent asked for this path in this log"
    combined: Counter = Counter()
    for counter in counts.values():
        combined.update(counter)
    verdict, _served = discovery_verdict(combined)
    total = combined.total()
    requests = "request" if total == 1 else "requests"
    agents = "agent" if len(counts) == 1 else "agents"
    detail = ", ".join(f"{name} ({_mix(counts[name])})" for name in counts)
    return f"{verdict} — {total} {requests} from {len(counts)} named AI {agents}: {detail}"


def _statuses_of(analysis: Analysis, name: str, path: str) -> Counter:
    record = analysis.record_for(name, CATEGORY_NAMED_AGENT)
    if record is None:
        return Counter()
    return record.discovery.get(path, Counter())


def _not_seen(analysis: Analysis) -> list[str]:
    seen = {record.label for record in analysis.named_agents}
    return [name for name in NAMED_AI_AGENTS if name not in seen]


def _agent_table(records: list[AgentRecord]) -> list[str]:
    if not records:
        return []
    width = max([len("agent")] + [len(record.label) for record in records])
    rows = [
        f"  {'agent':<{width}}  {'requests':>8}  {'paths':>5}  "
        f"{'first seen':<20}  {'last seen':<20}  statuses"
    ]
    for record in records:
        rows.append(
            f"  {record.label:<{width}}  {record.requests:>8}  {record.unique_paths:>5}  "
            f"{_iso(record.first) or '-':<20}  {_iso(record.last) or '-':<20}  "
            f"{_mix(record.statuses)}"
        )
    return rows


def _no_agent_traffic(analysis: Analysis) -> list[str]:
    rows = [
        "NO NAMED AI AGENT TRAFFIC IN THIS LOG",
        "",
    ]
    rows.extend(_wrap(
        f"{analysis.requests} request(s) were read, and none claimed to be one of the 12 named "
        f"AI agents. This is not a report that no agent visited: it says this log contains no "
        f"such claim, and a server that is not logging at all produces exactly this picture."
    ))
    rows.append("")
    rows.extend(_wrap(
        f"{TOOL_NAME} was written for a host that kept none — {NO_LOG_HOST} kept none until "
        f"2026-09-21 — so a zero from a host with logging switched off says nothing about "
        f"agents. README.md shows how to switch it on in Caddy."
    ))
    if analysis.coverage_seconds is not None and analysis.coverage_seconds < SHORT_WINDOW_SECONDS:
        rows.append("")
        rows.extend(_short_window_note(analysis))
    rows.append("")
    rows.append("  no named AI agent requested /llms.txt, /robots.txt or /sitemap.xml in this log")
    rows.append("")
    rows.append("  what this log does contain")
    for category in CATEGORY_ORDER:
        count = analysis.by_category[category]
        if count:
            rows.append(
                f"    {CATEGORY_LABELS[category]:<20}{count:>6}  "
                f"({_percent(count, analysis.requests)})"
            )
    unknown = analysis.unknown_clients
    if unknown:
        rows.append("")
        rows.append(f"  unrecognised user agents (top {TOP_CLIENTS})")
        for client, count in unknown:
            rows.append(f"    {count:>6}  {client}")
    rows.append("")
    rows.extend(_wrap(
        "Only requests that reached this server and were written to this log are counted."
    ))
    return rows


def _short_window_note(analysis: Analysis) -> list[str]:
    return _wrap(
        f"This window is {_duration(analysis.coverage_seconds)} long: the counts describe that "
        f"window only, not the site's history."
    )


def _no_readable_lines(analysis: Analysis) -> list[str]:
    rows = [
        "CANNOT ANSWER — nothing in the input could be read as an access log",
        "",
    ]
    rows.extend(_wrap(
        "No report was produced, because no line was recognisable as a Caddy JSON or "
        "common/combined access line. An empty result here is not a count of zero agents."
    ))
    rows.append("")
    rows.extend(_wrap(
        f"If the web server keeps no access log, there is nothing to trace. {TOOL_NAME} was "
        f"written for a host in that state — {NO_LOG_HOST} kept none until 2026-09-21 — and a "
        f"host with no log cannot be analysed until logging is switched on. README.md shows how "
        f"to switch it on in Caddy."
    ))
    rows.append("")
    rows.extend(_wrap(
        "If the server does write a log, the format may have changed: this tool reads Caddy JSON "
        "and the common/combined format, and it refuses rather than guesses. A third format is a "
        "recorded decision, not a configuration file."
    ))
    return rows


def _wrap(text: str, indent: str = "", width: int = 92) -> list[str]:
    words = text.split()
    rows: list[str] = []
    current = indent
    for word in words:
        candidate = f"{current} {word}" if current.strip() else f"{current}{word}"
        if len(candidate) > width and current.strip():
            rows.append(current)
            current = f"{indent}{word}"
        else:
            current = candidate
    if current.strip():
        rows.append(current)
    return rows


# -- JSON rendering -----------------------------------------------------------


def _discovery_json(analysis: Analysis, path: str, seen: dict) -> dict:
    """One discovery file in the JSON document, with every figure named.

    ``requests_from_all_clients`` and ``named_agent_requests`` are different numbers on
    purpose: the first counts every client, the second only the twelve named agents. W1
    found the earlier shape letting a reader take the first for the second.
    """

    named = _merge(_named_agent_statuses(analysis, path).values())
    verdict, served = discovery_verdict(named) if seen["agents"] else ("NOT REQUESTED", False)
    return {
        "agents": sorted(seen["agents"]),
        "named_agent_requests": named.total(),
        "named_agent_statuses": {str(code): count for code, count in sorted(named.items())},
        "requests_from_all_clients": seen["requests"],
        "statuses_from_all_clients": {
            str(code): count for code, count in sorted(seen["statuses"].items())
        },
        "verdict": verdict,
        "served": served,
    }


def _merge(counters) -> Counter:
    merged: Counter = Counter()
    for counter in counters:
        merged.update(counter)
    return merged


def _record_json(record: AgentRecord) -> dict:
    return {
        "agent": record.label,
        "category": record.category,
        "requests": record.requests,
        "unique_paths": record.unique_paths,
        "first_seen": _iso(record.first),
        "last_seen": _iso(record.last),
        "statuses": {str(code): count for code, count in sorted(record.statuses.items())},
        "discovery": {
            path: {
                "requested": True,
                "requests": sum(counter.values()),
                "statuses": {str(code): count for code, count in sorted(counter.items())},
            }
            for path, counter in sorted(record.discovery.items())
        },
    }


def render_json(analysis: Analysis) -> dict:
    state = analysis.state
    dominant = analysis.dominant_client
    document: dict = {
        "tool": TOOL_NAME,
        "version": __version__,
        "state": state,
        "claim_boundary": CLAIM_BOUNDARY,
        "sources": [
            {
                "name": source.name,
                "format": source.fmt,
                "lines_read": source.lines_read,
                "requests_read": source.requests_read,
                "lines_not_requests": source.lines_not_requests,
                "diagnostics": list(source.diagnostics),
            }
            for source in analysis.sources
        ],
        "coverage": {
            "first_seen": _iso(analysis.first),
            "last_seen": _iso(analysis.last),
            "duration_seconds": analysis.coverage_seconds,
            "short_window": (
                analysis.coverage_seconds is not None
                and analysis.coverage_seconds < SHORT_WINDOW_SECONDS
            ),
        },
        "totals": {
            "requests": analysis.requests,
            "by_category": {
                category: analysis.by_category[category] for category in CATEGORY_ORDER
            },
            "named_agent_requests": analysis.named_agent_requests,
            "agent_share": round(analysis.agent_share, 6),
        },
        "named_agents": [_record_json(record) for record in analysis.named_agents],
        "named_agents_not_seen": _not_seen(analysis),
        "search_crawlers": [_record_json(record) for record in analysis.search_crawlers],
        "declared_self": {
            "declarations": list(analysis.declarations),
            "matched": [_record_json(record) for record in analysis.declared_self],
            "unmatched": analysis.unmatched_declarations(),
        },
        "unrecognised_clients": [
            {"user_agent": client, "requests": count}
            for client, count in analysis.unknown_clients
        ],
        "dominant_client": (
            {
                "user_agent": dominant.user_agent,
                "requests": dominant.requests,
                "share": round(dominant.share(analysis.requests), 6),
                "category": dominant.category,
                "note": (
                    "The tool cannot tell whether this is the site's own monitoring. Declare it "
                    "with --self if it is."
                ),
            }
            if dominant
            else None
        ),
        "discovery": {
            path: _discovery_json(analysis, path, seen)
            for path, seen in analysis.discovery.items()
        },
        "top_agent_paths": [
            {"path": path, "requests": count}
            for path, count in analysis.agent_paths.most_common(TOP_PATHS)
        ],
        "agent_missing_paths": [
            {
                "path": item.path,
                "requests": item.requests,
                "statuses": {str(code): count for code, count in sorted(item.statuses.items())},
                "agents": sorted(item.agents),
            }
            for item in sorted(analysis.missing.values(), key=lambda m: (-m.requests, m.path))
        ],
    }
    if state == STATE_NO_AGENT_TRAFFIC:
        document["notice"] = (
            "No request in this log claimed to be one of the 12 named AI agents. This is not a "
            "report of zero agent activity: the server may not be logging requests at all. "
            f"{NO_LOG_HOST} kept no access log until 2026-09-21, so a zero from a host in that "
            "state says nothing about agents."
        )
    elif state == STATE_NO_READABLE_LINES:
        document["notice"] = (
            "Nothing in the input could be read as an access log line, so no report was "
            "produced. This is not a count of zero agents. A server that keeps no access log "
            f"({NO_LOG_HOST} kept none until 2026-09-21) cannot be analysed at all."
        )
    return document


def render_json_text(analysis: Analysis) -> str:
    return json.dumps(render_json(analysis), indent=2, sort_keys=False) + "\n"
