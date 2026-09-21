# Design

What `agenttrace` is made of, which choices were made in building it, and the measurements
taken while making them. The choice itself, with its authority and its acceptance criteria,
is in [`RECORD.md`](../RECORD.md) (alternatives A1–A8). This document is the detail behind
that table; [`README.md`](../README.md) is how to run the thing.

Written 2026-09-21 by Quill, the same day the tool was built, extended the same day after
**Rook's independent review** (W1) found eleven defects, six of which changed behaviour: the
discovery verdicts below 400 (D13), the JSON's discovery counts, the refusal to read a
one-quoted-field combined line, an invented `/` path, unchecked status ranges, and a
present-tense claim about a host that had started logging. The review also reproduced every
measurement in this document from the raw fixtures independently. Every number below was measured
on this machine on that date, and each one says what it does not establish.

## The shape

One pass, four stages, no state outside the process:

```
argv / stdin
   │  cli.expand_targets      globs expanded, duplicates dropped, stdin named
   ▼
files, stdin
   │  cli.analyse_stream      first 200 lines decide the format (or --format pins it)
   ▼
parse.parse_line             one line -> Entry(timestamp, method, path, status, user_agent)
   │                          or None, counted as "not read as requests"
   ▼
classify.classify            user-agent string -> Claim(category, agent, label)
   ▼
report.Analysis.add          one pass of counters, path sets and discovery tallies
   │
   ├── report.render_text    the report a person reads
   └── report.render_json    the same analysis as a document
```

Nothing is written to disk, nothing is cached, and no address is ever put into `Entry` — so
no later rendering bug can print one.

## D1. A package of four small modules, entered by `python3 -m agenttrace`

| Module | Lines | Owns |
| --- | --- | --- |
| `classify.py` | 237 | the user-agent taxonomy, as data plus one ordered lookup |
| `parse.py` | 270 | both formats, format detection, path and timestamp normalisation |
| `report.py` | 490 | accumulation, the text report, the JSON document |
| `cli.py` | 224 | arguments, inputs, exit codes, output |

Chosen because parsing, classifying, aggregating and rendering fail in different ways and are
tested separately; a single 1,200-line script would have to be read whole by any reviewer, and
the brief fixes the invocation anyway. Rejected: one standalone file (no unit tests without
import gymnastics), and a script plus a library (two entry points to keep honest).

## D2. The format is detected per file, with an override

A file is assumed to be one format. The first 200 non-blank lines are sniffed: JSON lines that
carry `ts`, `status` and a `request` object vote Caddy; lines matching the combined pattern
vote combined; the majority wins. `--format caddy|combined` pins the parser instead, and an
undecided file is read line by line, trying both.

Rejected: requiring `--format` always (the tool would need per-server knowledge it cannot
have); a single unified regex over all log shapes (Caddy's JSON is not a line format a regex
can read safely); a config file naming each server's format — `CONTEXT.md` caps the scope at
one format rather than a config file, and detection is what keeps two formats inside that cap.

Measured on the fixture corpus: 55 parsed requests from Caddy lines and 19 from combined
lines, each detected from its own file with no flag. `malformed.log` detects as combined and
reads 2 of its 6 lines, counting the other 3 non-blank lines as not-read rather than dropping
them. **Not established:** that either detector is right for a log shape not in the fixtures,
or that a file mixing both formats would be detected usefully (that is what `--format` is for).

## D3. Classification is an ordered rule list, not a list of names in code

Order: the twelve named agents (longest token first) → search crawlers → other bots →
browsers → unknown. Each stage is a tuple of tokens matched case-insensitively against the
string.

The order is the design. **56 of the 74 parsed fixture requests carry a user-agent string
beginning `Mozilla/`, and only 9 of those are browsers** — a browser test placed first would
swallow 47 of 74 requests (63%) into "browser", including nearly every crawler. Longest-token
ordering inside the named stage is what keeps `Applebot-Extended` out of `Applebot` (a search
crawler) and `Google-Extended` out of `Googlebot`; both are asserted in `tests/test_classify.py`.

The twelve names are exactly the brief's list. Anything else that is plainly a robot —
`meta-externalfetcher`, `Amazonbot`, `SemrushBot`, `python-requests`, a headless browser — is
counted in "other bot" rather than quietly merged into the named list, because the report's
headline figure is "claimed by a named AI agent" and widening that list would silently change
its meaning.

Rejected: a community crawler list fetched at run time (breaks the no-network, no-dependency
constraint, and would make the counts depend on someone else's edits); a per-vendor parser
with verification of published IP ranges (addresses are not read at all — see D4).

**Not established:** that vendors keep sending the strings the fixtures use. `Google-Extended`
is worth watching in particular — it is a `robots.txt` user-agent token rather than a crawler
with its own user-agent, so a `Google-Extended` line in a log is a claim that may never appear
in practice. The tool reports the claim if it sees it; it does not pretend the token implies a
distinct crawler.

## D4. The client address is never extracted

The combined parser reads the first field only as `\S+` to skip it; the Caddy parser never
touches `remote_ip` or `client_ip`. `Entry` has five fields, none of them an address, so the
address cannot reach a renderer even by mistake. `tests/test_report.py` asserts that the
fixtures *do* contain addresses and that no rendering of any fixture contains one.

There is a consequence outside the tool: **a log is itself a store of addresses**. Caddy
writes `request>remote_ip` (and `request>client_ip` since v2.7) on every access line. The
README's enablement snippet therefore deletes both fields with a `format filter` block, and
offers `ip_mask` truncation as the alternative for anyone who wants a network but not a host.
That does not make the log anonymous, and the tool does not claim it does.

Rejected: parsing the address and redacting at print time (one forgotten path from a leak);
hashing it to count unique visitors (a question this tool does not answer, and a value worth
not creating).

## D5. A path is the request target with its query string removed

`/pricing?utm_source=llms` and `/pricing` are one path. Measured on the fixtures: the named
agents' unique request targets fall from **13 raw to 11 normalised**, and all clients' from
**17 to 14**; three request targets carried a query string. Without normalisation, the top
paths and the "asked for and did not get" list fragment over tracking parameters — and a 404
for `/x?a=1` and a 404 for `/x` are one missing page, which is the list the site can act on.

Fragments are removed too (`#...` is never sent by a browser, but appears in some logs and in
absolute request targets). An absolute request target (`GET https://host/a/b`) is reduced to
its path.

**Not established:** that no query string carries a distinction worth keeping. If a real log
shows one — a search endpoint where the parameter *is* the page — this is the choice to
revisit, and it would be a recorded one.

## D6. Times are normalised to UTC ISO 8601

Both formats are converted to an aware UTC `datetime` and printed as `YYYY-MM-DDTHH:MM:SSZ`.

Measured shapes in the fixtures: Caddy's epoch float (`1789376400.0`), and `%d/%b/%Y:%H:%M:%S
%z` with both `+0000` and `+0200` offsets — the `+0200` line (10:00Z) is asserted to sort
correctly against the `+0000` ones. First/last sighting and any future multi-file run depend on
comparable instants, which the native strings are not.

The month name is parsed with an explicit table rather than `strptime`'s `%b`, because `%b`
follows the process locale: under a non-English locale a log written in English would fail to
parse, which is a bug that only shows up on someone else's machine.

**Not established:** that a server's clock or time zone is correct, or that the log's first and
last lines bound the window exactly (a rotated or truncated file bounds it only where it is).

## D7. Three outcomes and three exit codes

| State | Exit | Why it is not the other one |
| --- | --- | --- |
| A report, with or without agent claims | 0 | Zero claims is an answer about the log |
| A parsed log with no named-agent claims | 0, with the no-agent notice | The notice says what the zero does and does not mean |
| Nothing recognisable as an access log | 2 | There is no answer to give; a script must be able to tell this from zero |
| Usage or input error | 1 | The caller can fix it and the reason is on stderr |

The alternative — exit non-zero whenever no agent is found — was rejected because an empty
week is a legitimate finding. The alternative in the other direction — print the normal report
with zeros — was rejected because it is exactly the report that would make a host with no
logging look like a host with no agents. That failure mode is the reason this tool exists, so
the honest-bravery case is the one that got the design attention. `tests/test_cli.py` asserts
the three codes, in process and through `python3 -m agenttrace` as a subprocess.

## D8. The discovery files, `/llms.txt` first

`/llms.txt`, `/robots.txt` and `/sitemap.xml`, matched on the normalised path
case-insensitively. The verdict for `/llms.txt` is the first thing printed after the claim
boundary, and each agent's row says whether it asked. "READ" means a named agent requested it
and the log records a status below 400; a 404 or 410 is reported as "REQUESTED BUT NOT SERVED",
which is a different finding and is left visible as one.

Rejected: reporting only a site-wide fact (an agent that never asked and an agent whose request
failed would look alike); reporting the raw request count without the status (a 404 for
`/llms.txt` is not "being read"). Only exact path matches count: case is folded, so
`/LLMS.TXT` counts, while `/sitemap_index.xml` is a different file and does not — the question
is whether the convention's own file was fetched.

**Not established:** that a 200 means the file was read by a model rather than fetched and
discarded. The tool counts fetches; that is all a log can carry.

## D9. The report's order is the argument

Claim boundary → source and coverage → `/llms.txt` verdict → discovery files → named-agent
table (with the agents *not* seen, named) → search crawlers → site-wide share → top agent paths
→ paths agents asked for and did not get. The closing line says what the log cannot show.

The alternative — a single table of all clients sorted by volume — was rejected because the
reader would have to know which rows were agents; the tool's whole value is that it does that
classification and then shows its work.

## D10. Rotated logs are piped, not read

Caddy compresses rolled files to `.gz` by default. agenttrace reads plain text; the README
shows `zcat access-*.log.gz | python3 -m agenttrace --stdin`. Reading `.gz` transparently was
rejected for now: `gzip` is in the standard library, so it is *cheap*, but every added input
shape is another thing the format detection and the tests must cover, and the brief's input
surface is a file, a glob or standard input. This is the first convenience to add if real use
asks for it.

## D11. No time window

There is no `--since`/`--until`. The report prints the first and last request in the log, which
is what a reader needs to know what the counts cover. A window would need its own decisions
(which timestamp, inclusive or not, what to say when the window is only partly covered) and
the brief does not ask for it: rotated files already segment the log by time, and `zcat | grep`
segments it exactly. `CONTEXT.md`'s success test says "this week"; that is a property of the
log you hand the tool, not of the tool.

## D12. A format the tool does not recognise is refused, with the fields it saw

Detection reads the first 200 lines of each source and decides `caddy` or `combined`. When
nothing parses, the report says which shape it saw and which fields it expected — for a JSON
log: the top-level keys present, the keys inside `request`, and the missing `ts`, `status` and
`request.uri` — and exits 2 without a report. When *some* lines parse and at least 20% (and at
least three) do not, the report carries a warning at the top saying the counts come only from
the lines that were read, and why the others were not.

The policy this implements: a changed schema is a **refused** input, never a plausible-looking
report. Two formats are supported; a third is a recorded decision, not a configuration file
(`CONTEXT.md`'s scope cap). This is what `docs/RECORDS.md`'s corpus rule means by registering a
choice before the work: an unrecognised format must fail loudly rather than silently answer a
different question.

Falsified by construction: `tests/fixtures/caddy-drifted.log` renames `request.uri` to
`request.path` and `status` to `status_code`. Before this decision the tool reported "cannot
answer" with no reason; now it names both. **Not established:** that the diagnostics describe
every real drift — a schema that keeps the field names and changes their meaning would still
parse.

## D13. The discovery verdicts are precise about statuses

"READ" means a named agent requested the path and a 2xx was recorded. `304 Not Modified` is
read as read, and says the client already held a copy. `301`/`302`/`307`/`308` are **not** read:
the file was not served at that path, and the verdict names the codes. `404` and `410` say
"requested but not served"; `401` and `403` say "refused"; `5xx` says "server error"; `0` — Caddy
records no status when the connection dies — says no response was recorded. Nothing below 400
counts as success: the earlier version of this tool did exactly that, and it would have answered
the question the tool exists to answer wrongly.

Similarly, a status outside `0` or `100–599` is not a status: the line is counted as not read
rather than rendered as a real response.

## D14. The site's own clients are declared, not guessed

The first real log showed the problem the plan could not have predicted: 17 of its 21 requests
were `FindMyNextBiteMonitor/1.0`, the site's own health check. A tool that presents those as
bots — or worse, as an agent, if the monitor claimed one of the twelve names — misleads its
reader about the only thing it is for.

Three mechanisms, in order of increasing knowledge:

1. **Health-check tokens** (`monitor`, `healthcheck`, `kube-probe`, `blackbox`, `uptime`,
   `pingdom`) count as another bot rather than as an unrecognised client. This is a guess about
   a *class*, and it is labelled as one.
2. **The dominance line.** When one undeclared client holds at least half the log (and at least
   five requests), the report names it and says the tool cannot tell whether it is the site's
   own monitoring, and how to declare it. Judgement, stated as judgement.
3. **`--self TOKEN`.** The operator's declaration, repeatable, which wins over every rule
   including the twelve names. Declared requests are set aside in their own section and their
   own category, and a declaration that matches nothing is reported as matching nothing.

Rejected: inferring "self" from the requested paths or the hostname (a guess dressed as a
finding); treating a dominating client as self automatically (it may be somebody else's crawler,
and saying so matters); hiding the category (a labelled guess beats a silent one).

## D15. The window's length is part of the answer

The coverage line carries the duration, and a window shorter than an hour says in words that the
counts describe that window only. The first real log is 408 seconds long; a count of one claimed
agent from it is a fact about 408 seconds, and the output should not let a reader forget that.
The threshold is a display decision, not a statistical one, and it is recorded so a later reader
can disagree with it deliberately. Rejected: refusing to report short windows (a short window is
real evidence about itself), and silence (which is how a seven-minute sample becomes a claim
about a site).

## Measurements

Taken 2026-09-21 on this machine: Linux 7.0.11, 13th Gen Intel Core i9-13900H, Python 3.11.3
(GCC 11.4.0). Times are wall clock, single run, warm page cache, no other load control — they
are order-of-magnitude figures, not a benchmark.

**The fixture corpus** (7 files, 26,886 bytes, 79 non-blank lines):

| Measure | Value |
| --- | --- |
| Requests read | 74 (55 from Caddy JSON lines, 19 from combined lines) |
| Claimed by a named AI agent | 35 |
| Search crawlers | 13 |
| Other bots | 10 |
| Browsers | 9 |
| Unknown (no usable user-agent) | 7 |
| User-agent strings beginning `Mozilla/` | 56, of which 9 are browsers |
| Named-agent unique targets, raw → query-stripped | 13 → 11 |
| All unique targets, raw → query-stripped | 17 → 14 |

**Throughput**, on a synthetic 200,000-line (~59 MB) Caddy JSON log, one request per line,
5,000 distinct paths, eight different user-agent strings:

| Mode | Wall clock | Throughput | Peak resident set |
| --- | --- | --- | --- |
| Text report | 1.90 s | ~105,000 lines/s, ~31 MiB/s | 21 MiB |
| `--json` | 1.99 s | ~100,000 lines/s, ~29.6 MiB/s | 21 MiB |

**Not established by that measurement:** how the tool behaves on a real log. The synthetic file
has one format, one line shape, a small path universe and no partial lines; a real log brings
mixed formats, long URLs, far more distinct paths (the analysis holds a path set per agent, so
memory grows with distinct paths, not with lines) and a slower disk. A 10-million-line log
would take roughly 90–100 seconds by this rate.

**The first real log** (W3, 2026-09-21): 21 Caddy JSON lines from `findmynextbite.food`,
window 2026-09-21T18:28:02Z → 18:34:50Z (408.36 seconds). **21 of 21 lines read as requests,
format detected with no flag** — the format claim's first evidence from a real server. Clients:
`FindMyNextBiteMonitor/1.0` 17, `curl/7.81.0` 2, one browser, one claimed `GPTBot`. The `GPTBot`
entry requested `/llms.txt` and got a 200, which the report states; the window is far too short
for that to be a finding about the site, and every entry shares one masked `/16`.

**The checks:** `python3 -m unittest discover -s tests -t .` runs 140 tests in about 0.2 s, with
no network and no fixture outside `tests/fixtures/`; `scripts/check-project.sh` byte-compiles
`agenttrace/` and `tests/` and then runs them; `make ci` exits 0 with `make records` clean.

## What the design does not establish

- That the twelve names match what the vendors send today, or that they will tomorrow. The
  list is a fixture-asserted table, not a verified registry.
- That either format is what any particular server writes. Two shapes are supported because
  they are the two a host is likely to have; a third is out of scope by decision (D2).
- That a claimed agent is an agent (D4 and the claim boundary), or that a fetched page was
  read (D8).
- That the tool has an answer at all for the host it was written for. It does not, yet: that
  host keeps no access log, and U2 in [`RECORD.md`](../RECORD.md) is blocked on that rather
  than approximated.
