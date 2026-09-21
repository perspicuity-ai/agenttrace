---
format: perspicuity-work/1
id: at-project
revision: 4
skill_version: 0.5.0
updated: 2026-09-21
created_at: "2026-09-21T11:48:05-06:00"
updated_at: "2026-09-21T12:34:00-06:00"
record_status: open
work_status: active
---

# Agenttrace

<!-- The project record and the project's Statement of Work (revision 3), now carrying the
     grant and the units it authorised (revision 4). Revision 1 — the frame, objectives,
     material conditions and the Run-era U1 grant — is preserved in commit 652a38d; read it
     beside this revision rather than instead of it. Keep "## Current position" and its labels:
     the dashboard reads them and `make records` fails without Work scope and Next. -->

## Current position

Principal and decider: David — owns the objectives and the ratification. Retains spending, outbound messages, external agreements, the release word for publication, any new dependency, and every decision about a host's configuration and what it stores.

Work owner: Quill (coordinator). Rook is named as the W1 reviewer, not the author.

Mode: `Run` — the principal ratified B1-amended and granted W1–W4 on 2026-09-21, so the record carries the granted units through to their returns and stops there. Earlier mode: `Plan`, from 2026-09-21T12:02:00-06:00 until this grant, which registered the Statement of Work (revision 3) and stopped at the requested grant. Earlier still: `Run`, 11:52:40–11:59:00-06:00, under which the tool was built ahead of the plan and committed at `c040601`.

Decision: `selected` — David ratified the recommended course B1-amended and granted units W1–W4 on 2026-09-21T12:33:00-06:00, on the basis of revision 3 of this record. The selection is his; the recommendation was Quill's; nothing outside the granted scope is authorised.

Work scope: units W1–W4 as registered in revision 3 — W1 an independent review of the artefact, W2 format-drift diagnostics and the unrecognised-format policy, W3 verification against a real access log, W4 the first real-host finding — plus restoring the real project checks in `scripts/check-project.sh`, which the propagated process documents replaced with a deliberately failing stub.

Work: the grant is recorded in Act, with the reviewer named and the frozen hashes. W1 is picked up (Rook, not the author); W2 is granted and follows W1's return; W3 and W4 are granted and blocked, because the host now writes a log but no copy is reachable from this environment (C12).

Outcome: unknown — no real log has been read here yet. The input now exists on the host and the host's config masks the address at write time (C13), but nothing about a host may be claimed until W3 reproduces the counts by hand.

Next: Quill — assess Rook's W1 return, then carry W2 to its return.

Waiting on: David — a readable copy of a window of the host's access log in this environment, which is what W3 and W4 need.

Blocked: W3 and W4. The log is written on the host at `/var/log/caddy/findmynextbite-access.log`, mode 0640, group `caddy`; this machine has no `/var/log/caddy`, no `caddy` binary, and `david` is not in the `caddy` group, and this session can neither use sudo nor fetch from the host (C12). W1 and W2 are not blocked.

Dependency: a copy of the log placed in the workspace (or the tool run on the host, with its output returned) unblocks W3 and W4. Nothing else outside this repository is needed.

Authority: the principal's ratification and grant of 2026-09-21, recorded in Act; his Statement of Work request of the same day (revision 3); and his brief of the same day (revision 1). David retains publication (Q4 answered: not in scope), spending, outbound messages, external agreements, dependencies, and any further change to a host's configuration.

| Stage | began_at | registered_at / exact basis revision | finished_at |
| --- | --- | --- | --- |
| Frame and Decide (Run) | 2026-09-21T11:49:00-06:00 | 2026-09-21T11:52:40-06:00 / revision 1, commit `652a38d` | 2026-09-21T11:52:40-06:00 |
| Act (Run grant, superseded) | 2026-09-21T11:52:40-06:00 | 2026-09-21T11:52:40-06:00 / U1 pickup plan, revision 1 | 2026-09-21T11:59:00-06:00 — tool built and committed; never accepted; grant superseded |
| Frame and Decide (Plan) | 2026-09-21T12:02:00-06:00 | 2026-09-21T12:12:00-06:00 / revision 3, the Statement of Work | 2026-09-21T12:12:00-06:00 — plan registered |
| Act (granted) | 2026-09-21T12:33:00-06:00 | 2026-09-21T12:34:00-06:00 / revision 3 ratified by David; grant and unit states in this revision | pending — W1 in progress |
| Review | 2026-09-21T12:33:00-06:00 | 2026-09-21T12:12:00-06:00 / criteria R1–R7, revision 3 | pending — no criterion assessed yet |

## Frame and Decide

**The problem.** The workspace asserts things about how AI agents see its sites and has never
checked. A rubric verdict exists; no observation does. The narrow question that started this is
whether `/llms.txt`, published on `findmynextbite.food`, is read by anyone — answerable from a
server's own access log and by no other means. **The frame adopted** is that the log is the
evidence: count what a server recorded, claim nothing beyond it. Two consequences are held
throughout: the answer is only as good as the logging that produced the log, and a user-agent
string is a self-declared claim rather than an identity.

**What changed in this revision.** The mode changed from executing to planning. The frame above
survives; what is new is that the courses of action are compared as complete courses, the
existing artefact is judged rather than extended, and no selection is made — the principal
ratifies.

| # | Fundamental objective | Source | Measure, direction and horizon |
| --- | --- | --- | --- |
| O1 | Observed visibility for our own sites: a count instead of an assumption | `CONTEXT.md`, "Outcomes" 1, from the principal's brief | Named-agent requests, unique agent paths and first/last sighting per log window, from one host's log; up; from the first real log onward |
| O2 | A tool others can run: no dependency, documented, testable offline | `CONTEXT.md`, "Outcomes" 2 | Runs on Python 3.11+ from an access log alone; a stranger can follow the README; tests pass with no network; up; judged by an assessor and later by use, after the release word |
| O3 | Answer the prompting question: has any named agent read `/llms.txt`? | `CONTEXT.md`, "Why it exists" | Count of named-agent requests for `/llms.txt` with their statuses, per log window; any non-zero count answers it; from the first real log onward |
| O4 | Keep the claim honest: counts of claims, never verified agents | `CONTEXT.md`, "The claim boundary" | Boundary sentence present in every report; no address printed; an empty result never rendered as a working report; every output |

Objectives are the principal's and are unchanged from revision 1; only their attribution is
restated here. No objective was added or dropped by the mode change.

### Material conditions

| # | Condition | Type | Basis | Affects | Resolver or change trigger |
| --- | --- | --- | --- | --- | --- |
| C1 | **Amended at revision 4.** Was: `findmynextbite.food` writes no access log — no `log` directive, and the app's access log goes to `/dev/null`. Now: the host writes Caddy JSON access logs at `/var/log/caddy/findmynextbite-access.log`, mode 0640, group `caddy`, rolling at 50 MiB with five files and 30 days kept, with the client address masked at write time (`ip_mask 16 32` on `remote_ip` and `client_ip`) | Given | Workspace copy `find-my-next-bite/ops/public.caddy`, updated 2026-09-21T12:30-06:00, plus the principal's report that he applied and verified it on the host; the running host was not inspected from here | W3, W4, the project's success test | Already triggered. The log exists; C12 decides whether W3 can run against it |
| C2 | No real log has been read by this tool, and no copy of one is reachable from this environment | Given | Search of this machine for any copy, 2026-09-21: none. The tool has only ever read its own synthetic fixtures | Every claim about agents; W3; the difference between "the tool runs" and "the tool has answered" | The log becoming readable here (C12). Until then no claim about a host may be made |
| C3 | The existing artefact: `agenttrace/` (five modules, 1,255 lines), seven synthetic fixtures, 89 tests passing in 0.2 s, `make ci` exit 0 | Given | Measured 2026-09-21; commit `c040601` and `make ci` | Alternatives B1–B3 and every estimate below | W1's review may qualify any of it; a defect does not change the alternatives unless it shows the approach is unsound |
| C4 | Python 3.11.3 available; standard library only; no network in the tests; no new dependency | Given | The principal's brief; `CONTEXT.md`, "What we are deliberately not doing" | All units; it is what excludes B4 as things stand | A relaxation of the dependency constraint reopens B4 |
| C5 | A user-agent string is self-declared and trivially spoofable | Given | HTTP; `CONTEXT.md`, "The claim boundary" | Every count; the wording of every output | Nothing changes this; the tool repeats it in its own output |
| C6 | Whether either supported format matches what the host will actually write — Caddy's JSON field names and versions, and the variants of the combined line | Uncertainty | The fixtures are synthetic; no real log has been seen | W2, W3; the risk that a real log parses into a wrong or empty report | W3 against a real log; W2 makes the failure loud in the meantime |
| C7 | **Resolved at revision 4.** Was: whether the principal would enable access logging at all. He did, on 2026-09-21; the value question it gated is now C12 | Uncertainty → resolved | The principal's grant message of 2026-09-21, and C1's evidence | W3, W4 | Closed. Recorded rather than deleted so the question is not reopened by accident |
| C8 | What a real log contains that is sensitive beyond the addresses the tool never reads — full URIs with query strings, hostnames, paths that identify a person | Uncertainty | No real log inspected; Caddy redacts `Cookie`, `Set-Cookie` and `Authorization` by default but not query strings | Whether a real-log fixture may be committed; what the README must say about retention | Q3, and the first real log's inspection during W3 |
| C9 | The twelve named agents are the right list for the principal's question | Assumption | The brief lists them; `CONTEXT.md` repeats the list | Classification and the headline figure | A real log showing an AI crawler outside the list, or a vendor renaming one; such a claim lands in "other bot" today, visibly |
| C10 | One agent session is the unit of the estimates below, and the measured seven-minute build is not a human-effort baseline | Assumption | The tool was produced in one six-minute span on 2026-09-21 by Quill in this runtime | Every estimate | A different runtime, or a human-paced session, invalidates the scaling; W1's return should revise the rest |
| C11 | **Partly resolved at revision 4.** The project's process documents were instantiated from a template written against Perspicuity 0.4.0 while the installed skill is 0.5.0. The principal propagated an updated set at commit `9e69ce2` (`AGENTS.md`, `docs/RECORDS.md`, `docs/records/README.md`, `scripts/check-project.sh`, `scripts/check_records.sh`), which resolves divergences 1–4 below and makes `make ci` fail loudly while `check-project.sh` is a stub | Given | `/home/david/.dsh/skills/perspicuity/SKILL.md` (0.5.0) against the updated documents; compared 2026-09-21 at `9e69ce2` | How a worker reads the process here; what the checks cover | Remaining: `AGENTS.md` still carries its unfilled "Standing constraints" placeholder, and `docs/RECORDS.md`'s naming example still shows a `sw-` id. Both are template artefacts; the template is a different repository (owner: David) |
| C12 | The host's access log is not readable from this environment: `/var/log/caddy` does not exist on this machine, there is no `caddy` binary, and `david` is not in the `caddy` group; this session cannot use sudo and cannot fetch from the host | Given | Measured on this machine 2026-09-21T12:33-06:00: `ls -la /var/log/caddy/` (no such directory), `id` (`uid=1000(david)`, no `caddy` group), `which caddy` (nothing), and a filesystem search for any copy of the log (none) | W3, W4 | A copy of a window of the log placed in this workspace, or the tool run on the host with its output returned; owner David |
| C13 | The host masks the client address at write time (`ip_mask 16 32` on `remote_ip` and `client_ip`), so the log holds a network, not a host | Given | Workspace copy `find-my-next-bite/ops/public.caddy`, updated 2026-09-21T12:30-06:00; the principal's message states the verification saw `75.159.0.0` | W3, Q3's fixture rules, the README's privacy note | Not a trigger for change: the tool never reads the field, and a fixture will strip it anyway |

**The divergences recorded at revision 3, and their resolution.** They were recorded rather than
repaired, because the template lives in another repository; the principal propagated an updated
document set the same day at `9e69ce2`, which settles 1–4. They are kept here so a reader of the
earlier revision can see what changed:

1. `docs/RECORDS.md`'s skeleton and `AGENTS.md` name `skill_version: 0.4.0`; the installed skill
   is 0.5.0. This record declares 0.5.0.
2. `docs/RECORDS.md` lists the acceptable `work_status` values without `in_review`, which the
   installed checker accepts (`perspicuity_dashboard/work.py`, `WORK_STATES`), and it does not
   state 0.5.0's extra requirement for `in_review` work: a `next_check` date, a machine-readable
   `review_due` date, and a `Review due` line naming the evidence source and owner.
3. Neither document mentions 0.5.0's working-mode declaration in `Current position`, the unit
   ladder (`planned → ratified → granted → picked up → returned → accepted`), or the grant's
   includes/excludes/stop-condition fields. `AGENTS.md` also points at the skill under
   `.codex/skills/…` (a symlink to the same install) and still carries its unfilled "Standing
   constraints" placeholder.
4. `docs/RECORDS.md`'s "codes in use" list omits `at`, the project code `CONTEXT.md` assigns.

### Alternatives

Complete courses of action, not features. Each could be carried out on its own. B1 is what the
committed artefact already represents.

| # | Course of action | What it delivers | Inputs and dependencies |
| --- | --- | --- | --- |
| B1 | **Finish and verify what exists**: keep both parsers, the classifier and the report; have the artefact independently reviewed (W1); add format-drift diagnostics (W2); verify against a real log (W3); record the finding (W4) | A tool that answers the question wherever a supported log exists, with its limits visible; the first real-host answer | The artefact at `c040601`; a reviewer; a real log for W3 and W4 |
| B2 | **Cut to the minimum**: keep one format (Caddy JSON), drop the search-crawler table, the `--json` document and the design documents; keep the twelve names, the discovery verdict, the missing-paths list and the honest empty states | The smallest thing that answers the `/llms.txt` question on this host | The artefact; a decision to abandon the combined format and machine output, both of which the brief asks for |
| B3 | **Stop until logging exists**: keep the code as an unexercised artefact, do no further work, and spend nothing until a log exists; revisit then | Nothing to maintain or be wrong about; no effort spent on a tool that may be unreadable data | The principal's answer to Q1; the Caddy snippet already in `README.md` |
| B4 | **Adopt an existing analyser** (for example a Caddy-JSON-capable log analyser plus a user-agent filter) instead of maintaining this one | A mature tool, no code of ours to keep | Breaks C4: a new dependency; also reports addresses and visitor identity, which O4 avoids |

### Consequences

Against the objectives, with the basis of each cell labelled: **(E)** measured evidence,
**(J)** judgement, **(?)** gap that could change the choice. Cost is in agent sessions, on C10's
basis.

| Course | O1 observed visibility | O2 public tool | O3 `/llms.txt` answer | O4 claim honesty | Cost to finish | Main risk |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | Full once a log exists: per agent, per path, per status **(E)**; unverified on real logs today **(?)** | Two formats, documented, 89 offline tests, no dependency **(E)** | Direct and prominent; demonstrated on fixtures **(E)** | Boundary in every output; addresses never read; tested **(E)** | ≈2–2.5 sessions, of which ≈0.75 (W3, W4) is blocked on Q1 **(J)** | A real log confirms nothing, or confirms a schema W2 did not anticipate **(?)** |
| B2 | Same on Caddy hosts; nothing on other servers **(J)** | Weaker: one format, no machine output, thinner docs; the brief asks for both **(E: brief)** | Same on this host **(J)** | Same **(J)** | ≈0.5 session to strip the extra surface, then the same review and verification **(J)** | Saving effort now, spending it later if a second host or a script consumer appears **(J)** |
| B3 | None until a log exists — which is also true of B1 today **(E)** | The code exists but is unexercised; no documentation work done **(E)** | None until a log exists **(E)** | The empty-state behaviour still protects the claim **(E)** | 0 sessions now; the Caddy enablement decision is the principal's either way **(J)** | If logging is enabled later, the tool starts cold and unverified; the repository looks finished while answering nothing **(J)** |
| B4 | Depends on the adopted tool's reports; per-agent detail needs bespoke filtering **(J)** | No dependency-free story; installation instructions instead of `python3 -m agenttrace` **(J)** | Possible but indirect **(J)** | Conflicts: those tools report addresses and visitor identity by default **(J)** | Hours of adoption work with no in-repo tests **(J)** | A dependency and a data posture the principal's brief forbids today **(E: C4)** |

**The decisive comparison.** B1 and B2 differ only in how much of the brief they keep; B2's saving
is about half a session against losing a format and the machine output the brief asks for, so B2
wins only if the principal wants to shrink the promise. B3 is not a cheaper B1: it costs nothing
now and defers all the risk, which is rational exactly while C7 is unanswered — and C7 is the
question this plan cannot settle. B4 is excluded by C4, not by preference.

### Recommendation

**Recommended: B1 amended.** Keep the artefact, have it independently reviewed (W1), add the
format-drift diagnostics (W2), and verify it on a real log before any claim about a host is made
(W3, W4). Quill recommends; David ratifies.

**Ratified by David on 2026-09-21T12:33:00-06:00**, with W1–W4 granted in that order and the
fences in the grant below. The recommendation is kept as written; the selection is recorded in
`Current position` and in Act.

The tradeoff accepted: the tool stays **unverified against reality** until logging is switched on,
so the plan spends its first session reviewing and hardening what exists rather than adding
capability, and it accepts that the first real log may still surprise it. If Q1 is answered "no,
this host will not log", the recommendation lapses to **B3** — the code is kept as an unexercised
artefact and the project's value falls to O2 alone. **What would warrant reconsideration:** a
third log format appearing in real use (the scope cap then cuts the supported set to one); the
dependency constraint being relaxed (B4 becomes viable); W1 finding the artefact unsound rather
than merely imperfect (rebuild rather than amend); or a real log showing that the query-stripped
path loses a distinction that matters.

### Open questions for the principal

| # | Question | Owner | Blocks |
| --- | --- | --- | --- |
| Q1 | Will `findmynextbite.food` write an access log, and with which address handling — delete the address fields, truncate them, or store them? | David | W3, W4; the project's stated success test; and the recommendation itself, since "no" moves it to B3 |
| Q2 | Do you ratify this Statement of Work, its units W1–W4, and the W2 amendment to the existing tool? | David | Every unit. Nothing is picked up before ratification |
| Q3 | If a log exists: may a redacted extract become a committed test fixture, and is anything beyond the address fields sensitive (query strings, paths, hostnames)? | David | W3's regression evidence, and any real-log fixture record |
| Q4 | Is publication of the tool in scope now, and to where? | David (release word) | The publication work, which is out of scope until answered |
| Q5 | Who assesses W1 — a second worker named by Quill, or David? The assessor must not be the author | David | W1's independence claim, and therefore the weight of its findings |

**Answered by the principal, 2026-09-21, in the grant.** **Q1: yes** — he applied access logging
to the host and verified it writes (C1, C13). **Q2: yes** — B1-amended is ratified and W1–W4 are
granted, W1 first. **Q3: yes** — a real-log extract may be committed as a fixture under four
rules: no addresses at all (strip the field even though it is masked upstream), no cookies, no
query strings, and the window it came from recorded in or beside the fixture; a small honest
extract beats a large one. **Q4: no** — publication is not in scope for this grant. **Q5:** the
W1 reviewer must be a named worker who is not Quill; **Rook** is named in `docs/ACTORS.md` and in
the grant below, and who assessed the review is recorded with its return.

### Decision index

| Record | Owner | State | Depends on |
| --- | --- | --- | --- |
| This record | Quill | open, `waiting` — Statement of Work registered at revision 3, awaiting ratification | Q2, and the principal's answers |
| Naming the coordinator | Quill | settled in `docs/ACTORS.md`, commit `36bafe9` | This record's identity, `at-project` |
| The Run-era U1 grant and pickup plan | Quill | superseded by the mode change; preserved at revision 1, commit `652a38d` | — |

No sub-record under `docs/records/` is required yet. The admission test will be met by: any change
to a published claim about a host (a `data-` or `rubric-` record before W3's finding is
published); committing any real log or extract as a fixture (a `data-` record before it is
committed); adding a third format or a dependency (a `tech-` record before the work).

## Act

### What exists, and when it was produced

| Artefact | Revision | Produced | State |
| --- | --- | --- | --- |
| Template import | commit `520f256` | before this record | committed |
| Coordinator named Quill | `docs/ACTORS.md`, commit `36bafe9` | 2026-09-21T11:49:00-06:00 | committed |
| Record revision 1: frame, objectives, conditions, design alternatives A1–A8, U1 grant and pickup plan | `RECORD.md`, commit `652a38d` | 2026-09-21T11:52:40-06:00 | committed, superseded by this revision |
| The tool: five modules, seven fixtures, 89 tests, `scripts/check-project.sh`, `Makefile` test target | commit `c040601` | 2026-09-21T11:52:40 → 11:59:00 | committed; built under the Run grant; **never accepted** |
| `README.md`, `docs/DESIGN.md`, `docs/ARCHITECTURE.md`, `TODO.md` | working tree, uncommitted | 2026-09-21T11:57 → 12:00 | uncommitted drafts; not covered by this plan |
| Revision 2 of this record (`work_status: submitted`, U1 reported delivered) | working tree, uncommitted | 2026-09-21T12:00 | superseded and discarded: `submitted` implies a ratified plan that never existed |
| This Statement of Work | `RECORD.md` revision 3 | 2026-09-21T12:12:00-06:00 | the plan |
| Process documents brought to Perspicuity 0.5.0, and `scripts/check-project.sh` replaced with a deliberately failing stub | commit `9e69ce2` | 2026-09-21T12:29:51-06:00 | committed by the principal; the coordinator's records untouched; `make ci` now fails until the real checks are restored |
| The grant, the named reviewer and the unit states | `RECORD.md` revision 4, `docs/ACTORS.md` | 2026-09-21T12:34:00-06:00 | this revision |

**Honest provenance.** The tool was built under the Run grant registered at revision 1, before the
principal changed the mode. That grant authorised building it; the mode change supersedes it. The
work therefore stands as an **artefact ahead of this plan**: evidence for the comparison above
(C3), and nothing more. It has not been reviewed by anyone other than its author, it has never
read a real log, and no part of it is ratified by being present in the repository. This plan is
able to reject all of it, and says below which parts it would keep, amend or discard.

### What this plan judges of the existing work

Every judgement is provisional on W1's review, and none of it is acceptance.

| Part | Judgement | Reason |
| --- | --- | --- |
| Caddy and combined parsers, per-file detection | **Keep**, subject to W1; amended by W2 | Measured: 74 of 74 fixture requests read, 55 Caddy and 19 combined, with no flag needed (C3) |
| Classifier order and the twelve names | **Keep**, subject to W1 | Measured: 56 of 74 fixture user-agent strings begin `Mozilla/` and only 9 are browsers, so a browser-first test would swallow 47 requests. The ordering is load-bearing and it is tested |
| Report renderers, `/llms.txt` verdict, missing-paths list, exit codes | **Keep** | The three honest states — a report, no agent traffic, cannot answer — are the failure mode this project exists to avoid, and they are asserted in tests |
| Address non-extraction and its test | **Keep unchanged** | A value never read cannot leak; weakening this needs a recorded `data-` choice |
| Fixtures and the 89 tests | **Keep as regression evidence only** | They are synthetic and establish internal consistency, not reality (C2, C6) |
| `README.md` | **Amend** | Keep the Caddy enablement, the limits and the privacy note; any present-tense claim about what agents do must go until W3 exists |
| `docs/DESIGN.md` | **Keep**, amended when W2 lands | It is the detail behind this plan's alternatives; its measurements are dated measurements and stay valid as such |
| `docs/ARCHITECTURE.md` | **Discard, or reduce to a pointer** | It duplicates `docs/DESIGN.md` decisions D1–D11 with no added basis |
| `TODO.md` | **Amend** | Its items are re-expressed here as Q1–Q5, units W1–W4 and the out-of-scope list |
| Any claim that the tool "works" on a real host | **Discard** | Not established; no real log has been read (C2) |

### Grant

Recorded 2026-09-21T12:34:00-06:00 before any unit was picked up.

- **Decider:** David, the principal. **Basis revision:** revision 3 of this record, the Statement
  of Work, ratified 2026-09-21T12:33:00-06:00. The recommendation was Quill's; the selection is
  David's.
- **Granted:** the recommended course B1-amended, and units W1–W4 in the sequence W1, W2, W3, W4.
- **Actor:** Quill (coordinator), with **Rook** named in `docs/ACTORS.md` as the W1 reviewer — a
  worker who is not the author. Any further worker is named in this record before its assignment.
- **Includes:** restoring the real project checks in `scripts/check-project.sh`; carrying out the
  registered W1 pickup plan; correcting defects W1 finds inside the brief and without changing
  the claim boundary; delivering W2's drift diagnostics and policy; running the tool against the
  real log and hand-counting its figures (W3); recording the first real-host finding (W4);
  amending `README.md`, `docs/DESIGN.md`, `docs/ARCHITECTURE.md` and `TODO.md` as the plan's
  judgements direct; local commits.
- **Excludes:** publication, pushing to a remote, deployment, spending and outbound messages
  (Q4: no); any new dependency; any change to a host's configuration; committing a real-log
  extract except under Q3's four rules and only after a `data-` record exists; any claim about a
  host that W3 has not hand-checked.
- **Stop condition:** stop and return to David if a unit needs a dependency, a per-server
  configuration, a third format, publication, or anything else outside this repository; if W3's
  counts cannot be reproduced by hand; if the log becomes readable only with a change to the
  host; or if any finding changes the problem, the comparison or the selection. Adapting the
  route inside this grant is the actor's call; amending the grant is not.

### Unit states

| Unit | State | Ratified basis | Grant | Pickup |
| --- | --- | --- | --- | --- |
| W1 | **picked up** 2026-09-21T12:35:00-06:00, in progress | revision 3 SOW, ratified by David 2026-09-21; grant above | as above | W1 pickup plan registered at revision 3 and frozen at revision 4 |
| W2 | granted, not picked up — follows W1's return | as above | as above | at its own pickup |
| W3 | granted, **blocked** on a readable log (C12) | as above | as above | at its own pickup, once the log is readable here |
| W4 | granted, **blocked** on W3 | as above | as above | at its own pickup after W3 |

### W1 pickup (in progress)

Frozen basis for the review, named by commit and by hash so the review cannot drift:

- The tool: commit `c040601` — `agenttrace/__init__.py` `e84fbe424deb`, `__main__.py`
  `ea323dbc1678`, `classify.py` `ef3352526618`, `cli.py` `e1b01eb8a37c`, `parse.py`
  `06cd75419d9e`, `report.py` `610bd272e1fe` (sha256 prefixes).
- The tests and fixtures: commit `c040601` — `tests/test_classify.py` `6961e1b085e1`,
  `test_cli.py` `454f7e9de527`, `test_parse.py` `ccb40bc515d8`, `test_report.py` `2af3cf2628bb`,
  `support.py` `d0b363eaad29`; fixtures `caddy-sample.log` `c89b3be4479b` and the six others.
- The drafts under review for their claims: `README.md` and `docs/DESIGN.md` as they stood when
  the review was assigned (uncommitted; the reviewer records the hashes it read).
- **Assignment:** Rook reviews the artefact against the brief, this plan and the claim boundary,
  following the W1 pickup plan steps 1–6. Rook modifies nothing; the return is a findings list
  with severity, evidence and a reproducible check each, plus what was verified, what could not
  be, and what was not examined.
- **Return destination:** this record, in Rook's name. Quill reproduces each finding and records
  the response; David accepts the review or asks for correction. Rook's completion is not
  acceptance.

### Scope of work

The units of the recommended course. Estimates are in agent sessions on C10's basis and are
judgement unless a measured figure is named.

| # | Result | Inputs / dependencies | Owner | Done when | Estimate |
| --- | --- | --- | --- | --- | --- |
| W1 | An independent review of the artefact at `c040601` against the brief, this plan and the claim boundary, with a defect list | The artefacts; a reviewer who is not the author (Q5) | Named reviewer, authority Quill; findings assessed by David | The review names the revision reviewed, the criteria applied, what it re-derived by hand rather than by re-running the suite, what it could not verify, and a reproducible check for each finding | 1 session (J). The surface is 1,255 package lines and 838 test lines |
| W2 | Format-drift diagnostics, and the written policy for a format the tool does not recognise | W1's findings; `parse.py`, `cli.py`, `report.py` states | Quill | A drifted JSON schema and a drifted combined line each produce a specific diagnostic naming the shape seen and the fields expected, never a plausible report; a partially unreadable source says so at the top of the report; new fixtures and tests assert both | ≤0.5 session (J); the touched surface measures 984 lines across three modules |
| W3 | Verification against a real log: counts hand-checked, detection confirmed, any mismatch turned into a fixture and a test | Q1's log; Q3's permission for any fixture | David provides the log; Quill verifies; an assessor other than the author checks the hand counts | Every headline figure in the report for that log is reproduced by an independent hand count; the log's source and window are named; any unreadable line is explained | ≤0.5 session (J). The tool analysed 200,000 synthetic lines in 1.9 s (E); the cost is the hand count, not the run |
| W4 | The first real-host finding, recorded: which named agents appeared, what they fetched, what they missed, and whether `/llms.txt` was read — with its window and its limits | W3; the `data-`/`rubric-` record required before publication | Quill writes; David owns publication | The record names the log source, its window and its counts, and states what the log cannot show; no claim exceeds the lines it rests on | ≤0.25 session (J) |

Publication of the tool (O2) is deliberately **not** a unit: it needs Q4's release word and a
destination, and estimating it now would be invention.

### W1 pickup plan

Registered now, before the unit is picked up, as 0.5.0 requires for the first unit.

1. **Freeze the revision.** The review names the exact commit it read (`c040601`, plus whatever
   W2 has amended by then) and does not review a moving tree.
2. **Read the brief first.** `CONTEXT.md`, this plan's objectives and fences, and `README.md`'s
   limits section — before the code, so the code is judged against the promise.
3. **Re-derive rather than re-run.** Hand-count one fixture end to end — requests, agents, unique
   paths, first and last sighting, statuses, discovery files, missing paths — and compare with the
   tool's own output. Re-running the suite is not a review; the suite may be wrong with the code.
4. **Attack the two promises.** No address in either output mode; an empty or unreadable input
   never rendered as a working report. Both get an attempt at falsification, not a re-read.
5. **Check the claims.** Every present-tense claim in `README.md` and `docs/DESIGN.md` against
   what is established; anything resting on a real host goes.
6. **Return the findings** in this record, in the reviewer's name, as a list with severity and a
   reproducible check each, plus what the reviewer could not verify. Quill does not assess it;
   David accepts it or asks for correction.

**Acceptance criteria for W1:** the assessor is not the author and is named; the reviewed revision
is named; at least one fixture is re-derived by hand; both promises have a falsification attempt;
each finding has a reproducible check; the return states what was not verified. A review that only
re-runs `make ci` does not meet this.

### Out of scope

| Not covered | Reason |
| --- | --- |
| Live capture, a daemon, a proxy, a dashboard, an external API or a hosted service | `CONTEXT.md`: capturing is the web server's job; a report is the deliverable |
| A third log format, or per-server parser configuration | `CONTEXT.md`'s scope cap: if a server cannot be read without its own configuration, cut the supported set rather than grow a config file. A third format needs a recorded `tech-` choice first |
| Reading `.gz` rotated logs directly | `zcat … \| python3 -m agenttrace --stdin` works; D10 in `docs/DESIGN.md` records the deferral |
| A time window (`--since`/`--until`) | D11: the log already segments by time, and a window needs its own decisions |
| Unique-visitor counting, address hashing, or any address-derived figure | `CONTEXT.md` and O4: addresses are not read at all |
| Changing the host's configuration, including enabling logging | The principal's decision and his host; this plan asks (Q1) and prepares the snippet only |
| Publication, deployment, spending, outbound messages | Retained by the principal |
| Deciding which agents matter commercially, or attributing business value to a fetch | Not answerable from a log; `CONTEXT.md`'s claim boundary |
| Rewriting the template's process documents | A different repository; the divergences are recorded above and reported instead |

### Grant requested

Requested at revision 3; **granted in full by David on 2026-09-21T12:33:00-06:00**, with
publication excluded (Q4) and Rook named as the W1 reviewer (Q5). The request is kept as
registered so the grant can be read against it. That David ratify:

1. the recommended course (B1 amended) and its units W1–W4 with the done-when above;
2. the W2 amendment to the existing artefact — format-drift diagnostics and the
   unrecognised-format policy;
3. Quill's authority to correct defects W1 finds, inside the brief and without changing the claim
   boundary, and to re-run the checks;
4. Quill's authority to name one reviewer for W1 and one assessor for W3, neither of them the
   author of the work being assessed, with the names recorded in this record before the
   assignment;
5. Quill's authority to run the tool against a real log once one exists, and to record the
   finding in this record — not to publish it.

**Explicitly not requested.** Publication, pushing to a remote, deployment, spending, outbound
messages; any new dependency; any change to any host's configuration or to what it stores;
committing a real log or any extract as a fixture without a separate recorded `data-` choice;
acceptance of the existing artefact — ratifying this plan is not accepting `c040601`, which W1
judges; and any selection among the alternatives, which is David's alone.

**Stop conditions.** Stop and return to David if a unit would need a dependency, a per-server
configuration, a third format, publication, or anything else outside this repository; if W1 finds
the artefact unsound rather than imperfect (that is a rebuild and a new plan, not a silent
change); if W3 shows the tool's numbers cannot be reproduced by hand; or if any answer to Q1–Q5
changes the frame, the comparison or the recommendation.

## Review

Criteria registered at revision 3, before any unit is picked up. Delivery acceptance is separate
from evidence of later benefit, and neither is inferred from the other.

| # | Criterion | Evidence source | Owner, window or trigger | Finding | Response |
| --- | --- | --- | --- | --- | --- |
| R1 | Each unit meets its registered done-when, and nothing is claimed beyond it | The unit's artefacts, tests and return | Unit owner at return; David accepts | Pending | — |
| R2 | Every number in every output is attributable to log lines, and the claim boundary is present wherever counts appear | Reports and JSON; the tests that assert the boundary | Quill at each return; re-checked at W3 | Pending | — |
| R3 | No client address is printed, in any mode, and the tests that assert it still contain addresses to find | `make ci`; `tests/test_report.py` | Quill at every change | Pending | — |
| R4 | A format the tool does not recognise, or a drifted one, produces a specific diagnostic and never a plausible report | The W2 fixtures and tests; W3's real log | Quill at W2's return | Pending | — |
| R5 | The first real-host finding names its log source and window, and its headline counts are reproduced by an independent hand count | W3's verification note; the assessor's check | Assessor at W3; David accepts W4 | Pending | — |
| R6 | `make ci` exits 0 and `make records` is clean at every return | Command output recorded in this record | Quill at every return | Pending | — |
| R7 | Delivery is not treated as benefit: "the tool runs" and "an agent was observed" stay distinct in every claim | This record and any published finding | David at acceptance | Pending | — |

No timed obligation exists yet, so no `next_check` is set: the plan waits on the principal's
answers, not on a date. When W3 has a log, its window and the review date belong here.

## Changes

**Revision 4**, 2026-09-21T12:34:00-06:00. Records the principal's grant and the units it
authorises, before any unit was picked up. Added: the mode change to `Run` with the earlier
modes and their reasons; the selection (`selected`, David, on revision 3's basis) in place of the
recommendation; Q1–Q5 answered; the grant with its decider, actor, includes, excludes and stop
condition; the unit-state table; the frozen revision and hashes for W1; W2, W3 and W4 as granted,
with W3 and W4 blocked; and C12 (the host's log is not readable from this environment) and C13
(the host masks the client address at write time). Amended: C1 (the host now writes the log), C2
(no real log has been read here), C7 (resolved: logging was enabled), C11 (the process documents
were propagated to 0.5.0 at `9e69ce2`, settling the four divergences). Source: the principal's
grant message of 2026-09-21. Reason: a grant is registered before the work it authorises. Affects:
W1–W4 and the project checks. No code was changed by this revision.

**Revision 3**, 2026-09-21T12:12:00-06:00. RECORD.md became the project's Statement of Work after
the principal changed the mode from `Run` to `Plan`. Added: the mode declaration with the earlier
mode and its reason; the objectives restated with sources, measures and horizons; the material
conditions with type, basis and resolver, including the four divergences between the inherited
process documents and the installed 0.5.0 skill; four complete courses of action (B1 the existing
artefact, B2 build much less, B3 stop until logging exists, B4 adopt another tool) with a labelled
consequence comparison; the recommendation (B1 amended) marked as a recommendation for David's
ratification; open questions Q1–Q5; the honest provenance of the artefact built ahead of this
plan; the plan's judgement of each part of it (keep, amend, discard); units W1–W4 with done-when
and estimates; W1's pickup plan; the out-of-scope list; the grant requested and not requested; the
stop conditions; and review criteria R1–R7. Work state set to `waiting` on ratification. Source:
the principal's planning brief of 2026-09-21. Reason: a plan must exist and be ratified before the
work it authorises. Affects: everything after this revision; nothing was implemented. Correction
committed after `93d8141`: the artefact's size was first written as 1,249 package lines and 805
test lines; the measured figures are 1,255 and 838, and the blocked-on-Q1 total was corrected from
1.5 to 0.75 sessions. No basis, comparison or recommendation changes.

**Revision 2** (uncommitted draft, 2026-09-21T12:00, never committed, superseded). It reported the
Run-era U1 delivery against acceptance criteria A1–A8 and set `work_status: submitted`. That state
is discarded here: `submitted` presumes a ratified plan, and none existed. Its material content —
that the tool exists, its measurements, and the one defect found and corrected during the build
(the other-bot token table was matched case-sensitively, so `HeadlessChrome` and `Go-http-client`
fell through to browser and unknown; the fixture counts caught it and the table is now folded to
lower case before matching) — is carried into Act above.

**Revision 1**, 2026-09-21T11:52:40-06:00, commit `652a38d`. Created the registered project
record: coordinator named, mode `Run` declared, frame and objectives attributed to `CONTEXT.md`,
material conditions recorded with evidence, design alternatives A1–A8 for the tool's
implementation compared, U1 selected, granted and picked up with acceptance criteria A1–A8, and
review criteria registered. Preserved as written; this revision supersedes its selection and its
grant, not its basis.
