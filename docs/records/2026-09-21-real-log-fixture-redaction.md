---
format: perspicuity-work/1
id: at-2026-09-21-real-log-fixture-redaction
revision: 1
skill_version: 0.5.0
updated: 2026-09-21
created_at: "2026-09-21T12:40:00-06:00"
updated_at: "2026-09-21T12:40:00-06:00"
record_status: open
work_status: waiting
---

# Admit a redacted real-log extract as a test fixture

<!-- Sub-record of the project record. It registers the conditions under which traffic from a
     real server may enter this repository, before any extract exists. The point of a real-log
     fixture is regression evidence, not volume. -->

## Current position

Parent: [RECORD.md](../../RECORD.md), revision 4.

Principal: David. Decider: David — he answered Q3 in his grant of 2026-09-21.

Work owner: Quill (coordinator).

Decision: `selected` — a redacted extract of the real access log may be committed as a test
fixture, under four rules, and only after this record exists. Basis: revision 4 of
[RECORD.md](../../RECORD.md), which records the answer verbatim.

Work scope: the redaction rules for any real-log fixture in this repository, and the first such
extract (a small window of the host's log) when the log becomes readable here.

Work: the rules are registered. No extract has been taken, because no copy of the log is reachable
from this environment (C12 in the parent record). The existing fixtures are synthetic; nothing in
this repository holds real traffic.

Outcome: unobserved — no real-log fixture exists yet, so no evidence of a real server's lines has
been added to the test suite.

Next: Quill — when a readable copy of the log arrives, take the extract under these rules, record
its window and the redaction applied, and commit it with the tests that use it.

Waiting on: David — a readable copy of a window of the host's access log.

Dependency: a copy of `findmynextbite-access.log` placed in this workspace unblocks the extract.
Without it this record stays open and no real-log fixture is committed.

## Frame and Decide

**The question.** The tests run on synthetic logs. A real log is the only thing that can show
whether the parser, the classifier and the aggregation meet what a real server writes — and the
plan makes that evidence a unit (W3). But committing a server's traffic into a repository is a
data decision, not a test detail: an access log records who asked for what, and the repository is
intended for publication.

**Alternatives.**

| Alternative | Consequence |
| --- | --- |
| Commit no real traffic, ever — synthetic fixtures only | Nothing to redact and no data obligation. Costs the one evidence path the plan names (W3): the parser stays verified only against logs we wrote ourselves |
| Commit a small redacted extract | Real lines become regression evidence. Costs a redaction procedure, a recorded window and a fixture that must stay redacted as it is edited |
| Commit a synthetic log reshaped to imitate the real one | No traffic leaves the server. Costs the evidence: the imitation encodes our assumptions, which is exactly what the real log was meant to test |
| Commit the whole log | Best volume of evidence. Costs the most privacy: full URIs, timings and paths of real visitors, in a repository intended for publication |

**Selection.** David chose the redacted extract and fixed the rules (2026-09-21). Recorded
verbatim, because they are his conditions rather than the tool's convenience:

1. **No addresses at all.** The host masks the client address at write time (`ip_mask 16 32`), and
   the fixture must still strip the field entirely, so the file cannot be re-identified.
2. **No cookies.** No `Cookie` or `Set-Cookie` header value, in any form.
3. **No query strings.** Request targets are recorded without them.
4. **The window is recorded,** in the fixture or beside it.
5. *His framing, which governs the size:* the point is regression evidence, not volume — a small
   honest extract beats a large one.

The preference this rests on: evidence about real behaviour, without turning the repository into a
store of other people's requests. **What would warrant reconsideration:** a real log arriving that
cannot be redacted without destroying the property it was meant to test (then take the test
evidence from a windowed run on the host, not from a committed file); or a change in what the host
logs that adds a new personal-data field.

## Act

Procedure for the first extract (registered before it is taken; adapting the route inside these
rules is the owner's call):

1. Take a small window — enough lines to cover each named agent seen and the discovery files, not
   more. Prefer a contiguous span so the first/last sighting in the report is meaningful.
2. Remove the address fields outright (`request.remote_ip`, `request.client_ip`, and any
   `X-Forwarded-For` style value) rather than masking or hashing them.
3. Remove any query string from `request.uri`, keeping the path.
4. Remove cookie and authorization material if any is present. Caddy redacts `Cookie`,
   `Set-Cookie` and `Authorization` by default; the fixture must not depend on that.
5. Record the source host, the window covered, the extraction date and the redaction applied in a
   header comment beside the fixture (a companion `.md`, since a JSON line format has no comment
   syntax) and in this record.
6. Name it so its origin is unmistakable: `tests/fixtures/real-<host>-<window>.log`.
7. Add the test that uses it, plus a check that the fixture still contains no address-like token
   and no `?` in a request target — the redaction has to survive later edits.

| # | Result | Inputs / dependencies | Owner | Done when |
| --- | --- | --- | --- | --- |
| 1 | A redacted real-log fixture with its provenance note | A readable copy of the host's log (Q1/C12 in the parent record) | Quill | The fixture is committed with its window and the redaction applied, and no address-like token or query string survives in it |
| 2 | A test that uses the fixture, and a check that the redaction holds | The fixture; the existing suite | Quill | `make ci` passes and the redaction check fails if an address-like token is reintroduced |

## Review

| Criterion | Evidence source | Owner, window or trigger | Finding | Response |
| --- | --- | --- | --- | --- |
| The committed fixture holds no address, no cookie material and no query string | The fixture file; the redaction check in the suite | Quill at the commit; re-checked on every later edit | Pending | — |
| The window and the redaction applied are recorded beside the fixture and in this record | The provenance note; this record | Quill at the commit | Pending | — |
| The fixture adds evidence the synthetic fixtures cannot: a real server's line shapes and statuses | The test that uses it; W3's verification note in the parent record | Quill at W3 | Pending | — |

## Changes

Revision 1, 2026-09-21T12:40:00-06:00. Created, with no extract taken: the rules exist before the
fixture does, which is the point of registering them separately from the parent record. Source:
David's answer to Q3 in his grant of 2026-09-21. Reason: admitting real traffic to the repository
changes what this project stores and publishes, so it needs a recorded choice before the work that
depends on it. Affects: W3 and the test suite.
