# To do

Open items, newest first. Anything with a timed obligation also lives in a record and shows up
in `make records`; this file is the human-readable list.

State at 2026-09-21, after the first real log was read. The units and their states are in
[`RECORD.md`](RECORD.md); this is the short list.

## Waiting on the principal

- **A longer window of the host's log.** The 408-second window that exists is parser evidence:
  it shows the tool reads what a real Caddy writes, and it cannot support a claim about agents.
  A week of it would make W4 a finding rather than a note. Owner: David.

## Blocked on the release word

- **Publishing `agenttrace`.** Q4 was answered "not in scope for this grant", so the repository
  stays local. Nothing else is needed for it: no dependency, no account, just the release word.

## Next by the plan

- **W3's final note and W4.** The hand-count is done against the 408-second window; the finding
  is recorded with its window and its limits. A longer extract extends it.
- **Verify the comment that the GPTBot line was not a test.** Every entry in the first window
  shares one masked `/16`, and two entries are the change's own `curl` calls, so the single
  claimed `GPTBot` request cannot be separated from a local test by this log. Ask David; until
  then the finding says so.

## Deliberately not doing yet

- **Reading `.gz` rolled logs directly.** `zcat access-*.log.gz | python3 -m agenttrace --stdin`
  works (D10 in [`docs/DESIGN.md`](docs/DESIGN.md)).
- **A time window (`--since`/`--until`).** Rotated files segment by time already (D11).
- **A third log format or per-server configuration.** `CONTEXT.md` caps this: if a server cannot
  be read without its own configuration, cut the supported set to one format.
- **A dashboard, a daemon or a hosted service.** The tool prints; plotting is someone else's tool.
- **Unique-visitor counting or address hashing.** Addresses are not read at all (D4).
