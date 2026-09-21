---
format: perspicuity-work/1
id: at-2026-09-21-real-log-fixture-redaction
revision: 3
skill_version: 0.5.0
updated: 2026-09-21
created_at: "2026-09-21T12:40:00-06:00"
updated_at: "2026-09-21T13:22:00-06:00"
closed_at: "2026-09-21T13:22:00-06:00"
record_status: closed
work_status: accepted
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

Work: the rules are registered, and the first extract has been taken under them — 21 entries from
the host's log, window 2026-09-21T18:28:02Z → 18:34:50Z, committed as
`tests/fixtures/real-findmynextbite-2026-09-21-1828Z.log` at `64c6847` with its provenance note and
a test that enforces the redaction. The unredacted copy stays in `var/`, which is gitignored and
was never committed.

Outcome: the repository now holds real traffic, redacted. The redaction holds mechanically: no
address-like token, no query string, no address, port, cookie or response-header material in the
committed file (`tests/test_real_fixture.py`). All three review criteria are met: the fixture
also did what only a real one could — it exposed the site's own monitor as 17 of 21 requests,
which no synthetic fixture had contained.

Next: none — every criterion is met and the delivery is accepted. A later extract, if one is
taken, is governed by the same rules and would be an amendment to this record rather than new
work.

Dependency: none outstanding. A longer window would extend the fixture's use, but the rules above
already govern it and need no change.

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
| The committed fixture holds no address, no cookie material and no query string | The fixture file; the redaction check in the suite | Quill at the commit; re-checked on every later edit | **Met.** `tests/test_real_fixture.py` asserts no address-like token, no query string, and no address, port, cookie, authorization or response-header key; `make ci` passes | Keep the check; it fails the build if the redaction is undone |
| The window and the redaction applied are recorded beside the fixture and in this record | The provenance note; this record | Quill at the commit | **Met.** `tests/fixtures/real-findmynextbite-2026-09-21-1828Z.md` records source, window, extraction, the four redactions and what the window cannot support; the test asserts the window is in it | — |
| The fixture adds evidence the synthetic fixtures cannot: a real server's line shapes and statuses | The test that uses it; W3's verification note in the parent record | Quill at W3 | **Met.** It is the only fixture written by a real server (Caddy's `tls` block, `client_ip`, an address masked to `/16`, a real monitor user-agent), and it is what exposed the site-monitor problem: 17 of its 21 requests were `FindMyNextBiteMonitor`, which the synthetic corpus had never contained. All 21 lines parse | The finding drove `--self`, the dominance line and the health-check tokens (parent record, W2) |

## Closure

Closed 2026-09-21 by Quill. Reason: all three registered criteria are met and the principal's
acceptance of unit W3 (recorded in [`RECORD.md`](../../RECORD.md) revision 8, 2026-09-21) covers
this record's delivery; no obligation remains. Evidence:
[`tests/test_real_fixture.py`](../../tests/test_real_fixture.py) for the redaction check,
[`tests/fixtures/real-findmynextbite-2026-09-21-1828Z.md`](../../tests/fixtures/real-findmynextbite-2026-09-21-1828Z.md)
for the provenance and the corrected `Set-Cookie` record, and commit `64c6847` for the extract
itself. The parent record stays open for its own promised observation at 2026-09-28.

## Changes

Revision 3, 2026-09-21T13:22:00-06:00. Closed as accepted. Source: the principal's acceptance of
W1–W4 on 2026-09-21, recorded at RECORD.md revision 8. Reason: nothing further is owed here, and
a record that keeps an accepted delivery open accumulates as an unowned queue item. Affects: the
corpus's open list only; the rules and the fixture are unchanged.

Revision 2, 2026-09-21T12:54:00-06:00. The first extract was taken and committed at `64c6847`,
with its provenance note and the redaction check, after the principal copied a window of the host's
log into the workspace. Source: the principal's follow-up of 2026-09-21T18:35Z. Reason: the
registered rules had a case to apply. Affects: the test suite, W3. Review criteria 1 and 2 are met;
criterion 3 waits on W3's final note.

Revision 1, 2026-09-21T12:40:00-06:00. Created, with no extract taken: the rules exist before the
fixture does, which is the point of registering them separately from the parent record. Source:
David's answer to Q3 in his grant of 2026-09-21. Reason: admitting real traffic to the repository
changes what this project stores and publishes, so it needs a recorded choice before the work that
depends on it. Affects: W3 and the test suite.
