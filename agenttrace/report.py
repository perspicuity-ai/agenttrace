"""Aggregate parsed requests and render the report.

Two renderings of the same analysis: a text report for a person and a JSON document
for a script. Both carry the claim boundary, and neither can carry a client address —
the analysis only ever sees the fields :class:`agenttrace.parse.Entry` holds.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from . import CLAIM_BOUNDARY, DISCOVERY_FILES, NO_LOG_HOST, TOOL_NAME, __version__
from .classify import (
    CATEGORY_LABELS,
    CATEGORY_NAMED_AGENT,
    CATEGORY_ORDER,
    CATEGORY_SEARCH_CRAWLER,
    NAMED_AI_AGENTS,
    Claim,
)
from .parse import Entry

STATE_REPORTED = "reported"
STATE_NO_AGENT_TRAFFIC = "no_agent_traffic"
STATE_NO_READABLE_LINES = "no_readable_lines"

TOP_PATHS = 10


@dataclass
class Source:
    """What was read from one file, or from standard input."""

    name: str
    fmt: str | None
    lines_read: int = 0
    requests_read: int = 0
    lines_not_requests: int = 0

    @property
    def label(self) -> str:
        return self.fmt or "undecided"


@dataclass
class AgentRecord:
    """One label: a named AI agent, a named search crawler, or a category."""

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


class Analysis:
    """Everything the report needs, accumulated in one pass."""

    def __init__(self) -> None:
        self.sources: list[Source] = []
        self.requests = 0
        self.by_category: Counter = Counter()
        self.by_label: dict[str, AgentRecord] = {}
        self.statuses: Counter = Counter()
        self.agent_paths: Counter = Counter()
        self.missing: dict[str, MissingPath] = {}
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
        if self.first is None or entry.timestamp < self.first:
            self.first = entry.timestamp
        if self.last is None or entry.timestamp > self.last:
            self.last = entry.timestamp

        record = self.by_label.get(claim.label)
        if record is None:
            record = AgentRecord(label=claim.label, category=claim.category)
            self.by_label[claim.label] = record
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

    def _records(self, category: str) -> list[AgentRecord]:
        rows = [r for r in self.by_label.values() if r.category == category]
        return sorted(rows, key=lambda r: (-r.requests, r.label.lower()))

    @property
    def named_agent_requests(self) -> int:
        return self.by_category[CATEGORY_NAMED_AGENT]

    @property
    def agent_share(self) -> float:
        return self.named_agent_requests / self.requests if self.requests else 0.0

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
        add(f"coverage  {_iso(analysis.first)} .. {_iso(analysis.last)}  ({analysis.requests} requests)")
    add("")

    if analysis.state == STATE_NO_READABLE_LINES:
        return "\n".join(lines + _no_readable_lines(analysis))
    if analysis.state == STATE_NO_AGENT_TRAFFIC:
        lines.extend(_wrap(CLAIM_BOUNDARY))
        add("")
        return "\n".join(lines + _no_agent_traffic(analysis))

    lines.extend(_wrap(CLAIM_BOUNDARY))
    add("")
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
    missing_agents = _not_seen(analysis)
    if missing_agents:
        lines.extend(_wrap(f"  not seen in this log: {', '.join(missing_agents)}", indent="  "))
    add("")

    if analysis.search_crawlers:
        add("Search crawlers seen")
        add("")
        lines.extend(_agent_table(analysis.search_crawlers))
        add("")

    add("Site-wide")
    add("")
    add(f"  requests in this log               {analysis.requests:>6}")
    for category in CATEGORY_ORDER:
        count = analysis.by_category[category]
        if category == CATEGORY_NAMED_AGENT:
            add(f"  claimed by a named AI agent        {count:>6}  ({_percent(count, analysis.requests)})")
        else:
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
                f"({analysis.status_mix(item.statuses)}; {', '.join(sorted(item.agents))})")
    else:
        add("  none — every path a named AI agent asked for was served")
    add("")
    lines.extend(_wrap(
        "Only requests that reached this server and were written to this log are counted. "
        "Requests that never arrived are invisible, and a page being served is not evidence "
        "that it was read."
    ))
    return "\n".join(lines)


def _statuses_of(analysis: Analysis, name: str, path: str) -> Counter:
    record = analysis.by_label.get(name)
    if record is None:
        return Counter()
    return record.discovery.get(path, Counter())


def _discovery_line(analysis: Analysis, path: str) -> str:
    """One sentence per discovery file: read, not requested, or requested and refused."""

    seen = analysis.discovery[path]
    names = sorted(seen["agents"])
    if not names:
        return "NOT REQUESTED — no named AI agent asked for this path in this log"
    counts = {name: _statuses_of(analysis, name, path) for name in names}
    total = sum(counter.total() for counter in counts.values())
    served = any(code < 400 for counter in counts.values() for code in counter)
    requests = "request" if total == 1 else "requests"
    agents = "agent" if len(names) == 1 else "agents"
    detail = ", ".join(f"{name} ({analysis.status_mix(counts[name])})" for name in names)
    verdict = "READ" if served else "REQUESTED BUT NOT SERVED"
    return f"{verdict} — {total} {requests} from {len(names)} named AI {agents}: {detail}"


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


def _mix(statuses: Counter) -> str:
    return " ".join(f"{code}:{count}" for code, count in sorted(
        statuses.items(), key=lambda item: (-item[1], item[0])))


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
        f"{TOOL_NAME} was written for a host in that state — {NO_LOG_HOST} keeps no access log — "
        f"so on that host this result says nothing about agents until logging is switched on. "
        f"README.md shows how to switch it on in Caddy."
    ))
    rows.append("")
    rows.append("  no named AI agent requested /llms.txt, /robots.txt or /sitemap.xml in this log")
    rows.append("")
    rows.append("  what this log does contain")
    for category in CATEGORY_ORDER:
        count = analysis.by_category[category]
        if count:
            rows.append(f"    {CATEGORY_LABELS[category]:<20}{count:>6}  ({_percent(count, analysis.requests)})")
    rows.append("")
    rows.extend(_wrap(
        "Only requests that reached this server and were written to this log are counted."
    ))
    return rows


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
        f"written for a host in that state — {NO_LOG_HOST} writes no access log — and it cannot "
        f"answer its own question there until logging is switched on. README.md shows how to "
        f"switch it on in Caddy."
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
            }
            for source in analysis.sources
        ],
        "coverage": {
            "first_seen": _iso(analysis.first),
            "last_seen": _iso(analysis.last),
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
        "discovery": {
            path: {
                "requests": seen["requests"],
                "agents": sorted(seen["agents"]),
                "statuses": {str(code): count for code, count in sorted(seen["statuses"].items())},
                "read": bool(seen["agents"]) and any(code < 400 for code in seen["statuses"]),
            }
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
            f"{NO_LOG_HOST} keeps no access log, so this result says nothing there until logging "
            "is switched on."
        )
    elif state == STATE_NO_READABLE_LINES:
        document["notice"] = (
            "Nothing in the input could be read as an access log line, so no report was "
            "produced. This is not a count of zero agents. A server that keeps no access log "
            f"(for example {NO_LOG_HOST}) cannot be analysed at all."
        )
    return document


def render_json_text(analysis: Analysis) -> str:
    return json.dumps(render_json(analysis), indent=2, sort_keys=False) + "\n"
