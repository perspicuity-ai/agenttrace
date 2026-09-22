# To do

Open items, newest first. Anything with a timed obligation also lives in a record and shows up
in `make records`; this file is the human-readable list.

State at 2026-09-21, after the first real log was read. The units and their states are in
[`RECORD.md`](RECORD.md); this is the short list.

## Waiting on the principal

- **An untouched, week-long window of the host's log** — the one outstanding obligation, kept by
  `next_check: 2026-09-28`. The windows so far (408 and 510 seconds) are parser evidence and a
  record of what happened while somebody was at the keyboard: no external agent appeared, and the
  one `GPTBot` line was the operator's own test. Extract supply is pre-authorised (standing
  permission, 2026-09-21), so this waits on the week elapsing, not on a request.
- **The two 404s the first window surfaced** (`GET /foods/impossible-beef/` and the malformed
  `GET /foods//`, both from FMNB's own monitor) are Find My Next Bite's, not this project's.
  **Closed 2026-09-21: recorded, not raised**, by David's decision. Nothing here touches another
  project's health check, and nothing is owed there either.

## Blocked on the release word

- **Publishing `agenttrace`.** Q4 was answered "not in scope for this grant", so the repository
  stays local. Nothing else is needed for it: no dependency, no account, just the release word.

## Next by the plan

- **Nothing until the checkpoint.** W1–W4 are delivered and accepted (RECORD.md revision 8), and
  every result in the scope is accounted for there. The next act is R8 at 2026-09-28.
- **The next extract must be one nobody is touching.** Enabling the logging produced the only
  notable entry in the first observation; repeating that would repeat the artefact.

## Deliberately not doing yet

- **Reading `.gz` rolled logs directly.** `zcat access-*.log.gz | python3 -m agenttrace --stdin`
  works (D10 in [`docs/DESIGN.md`](docs/DESIGN.md)).
- **A time window (`--since`/`--until`).** Rotated files segment by time already (D11).
- **A third log format or per-server configuration.** `CONTEXT.md` caps this: if a server cannot
  be read without its own configuration, cut the supported set to one format.
- **A dashboard, a daemon or a hosted service.** The tool prints; plotting is someone else's tool.
- **Unique-visitor counting or address hashing.** Addresses are not read at all (D4).
