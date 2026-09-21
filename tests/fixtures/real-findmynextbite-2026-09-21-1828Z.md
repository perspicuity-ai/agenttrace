# Real-log fixture: `real-findmynextbite-2026-09-21-1828Z.log`

Provenance for the one fixture in this directory that came from a real server. The rules it
follows are registered in
[`docs/records/2026-09-21-real-log-fixture-redaction.md`](../../docs/records/2026-09-21-real-log-fixture-redaction.md);
what was actually done to the bytes is recorded here.

| | |
| --- | --- |
| Source | `findmynextbite.food`, Caddy JSON access log (`/var/log/caddy/findmynextbite-access.log` on the host) |
| Window | 2026-09-21T18:28:02Z → 2026-09-21T18:34:50Z — 408 seconds |
| Extracted | 2026-09-21, copied from the host by David; the working copy stayed in `var/`, which is gitignored and not committed |
| Entries | 21, all Caddy JSON access lines, one format, no transformation of field names or values beyond the redaction below |
| First read by this tool | 2026-09-21, W3: 21 of 21 lines read as requests, format detected as `caddy` with no flag |

## Redaction applied to every line

1. `request.remote_ip`, `request.client_ip` and `request.remote_port` **removed entirely**. The
   host already masks the address to `/16` and `/32` at write time, so the field held only
   `75.159.0.0`; it is still removed rather than masked, so the fixture cannot be re-identified
   and does not depend on the mask.
2. Query strings **removed** from `request.uri`. One entry was affected:
   `/api/discovery?q=Vegan%20Supply` is recorded as `/api/discovery`.
3. `resp_headers` **removed**. The tool never reads it, and response headers can carry
   `Set-Cookie`. No `Cookie`, `Set-Cookie` or `Authorization` value was present in these lines
   before removal, in either request or response headers.
4. No other field was changed. `ts`, `status`, `request.method`, `request.host`, `request.uri`,
   `request.headers.User-Agent`, `request.headers.Accept`, `request.tls` and the remaining
   top-level fields are as the server wrote them.

## What this window can and cannot support

It is **408 seconds** of one host, taken minutes after access logging was switched on. It is
evidence that the tool reads what a real Caddy writes — field shapes, statuses, a real
`User-Agent` array, a real masked address field. It is **not** evidence about how agents treat the
site: a seven-minute window says nothing about a week, and one of the requests in it claims to be
`GPTBot` while every entry in the window shares a single masked `/16`, which the log cannot use to
separate a local test from a remote crawler.

The busiest client in the window is `FindMyNextBiteMonitor/1.0` with 17 of the 21 requests: the
site's own monitor. Two entries are `curl/7.81.0` from the change that enabled logging. Treat the
counts here as parser evidence and as a record of what one short window contained, nothing more.
