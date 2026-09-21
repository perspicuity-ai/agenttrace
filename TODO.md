# To do

Open items, newest first. Anything with a timed obligation also lives in a record and shows up
in `make records`; this file is the human-readable list.

State at 2026-09-21, after the first real log was read. The units and their states are in
[`RECORD.md`](RECORD.md); this is the short list.

## Waiting on the principal

- **An untouched, week-long window of the host's log.** The windows so far (408 and 510 seconds)
  are parser evidence and a record of what happened while somebody was at the keyboard: no
  external agent appeared, and the one `GPTBot` line was the operator's own test. A week nobody
  is touching is what turns W4 into a finding about agent traffic. Owner: David, at the
  2026-09-28 checkpoint.

## Blocked on the release word

- **Publishing `agenttrace`.** Q4 was answered "not in scope for this grant", so the repository
  stays local. Nothing else is needed for it: no dependency, no account, just the release word.

## Next by the plan

- **W4's finding stands corrected:** zero external AI agents in the 510-second window, and the
  only named-agent line in it is the operator's own synthetic `GPTBot` request. Recorded at
  RECORD.md revision 7 with the earlier text preserved.
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
