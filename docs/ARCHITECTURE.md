# Architecture

Reduced to the shape and an index on 2026-09-21: the first version duplicated
[`docs/DESIGN.md`](DESIGN.md), which carries the same decisions with their measurements and the
alternatives that were rejected. Duplication is how two documents start disagreeing.

## The shape

One process, one pass, no state on disk:

```
argv / stdin → cli (globs, --stdin, --self, --format, exit codes)
             → parse (Caddy JSON | common/combined → Entry: time, method, path, status, agent)
             → classify (named AI agent | search crawler | other bot | browser | unrecognised
                         | declared your own)
             → report.Analysis (counters, path sets, discovery verdicts, client identity)
             → text report or --json document
```

`Entry` has five fields and no address, so no renderer can print one. Nothing is fetched,
captured or cached; the only input is a log file or standard input.

## Where the decisions are

| What | Where |
| --- | --- |
| The choices, their alternatives and the measurements behind them | [`docs/DESIGN.md`](DESIGN.md) — D1–D15 |
| The plan, the grant, the units and their states, the review criteria | [`RECORD.md`](../RECORD.md) |
| The rules for the one fixture taken from a real server | [`docs/records/2026-09-21-real-log-fixture-redaction.md`](records/2026-09-21-real-log-fixture-redaction.md) |
| How to run it, and what it does not do | [`README.md`](../README.md) |

## What is deliberately absent

- **Live capture, a daemon, a dashboard, an external API.** It reads a file and stops.
- **Client addresses in the input model or the output.** Including in the JSON document. The host
  masks them at write time as well; the tool does not depend on that.
- **A configuration file.** Two formats, auto-detected. If a third server needs its own
  configuration, the supported set shrinks to one format instead (`CONTEXT.md`, scope cap).
- **A time window.** The report prints the window it covers, and its duration, instead.
- **Verification of any agent.** A user-agent string is a claim, and every output says so.
- **Business value.** A fetched page is not a read page, and a served page is not a sale.
