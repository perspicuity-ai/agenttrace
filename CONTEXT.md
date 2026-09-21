# Context

What agenttrace is, why it exists, and what "good" looks like.

**Project code:** `at`

## The product, in one paragraph

Give `agenttrace` a web server's access log, and it reports what AI agents actually did on the
site: which named agents visited, what they fetched, what they asked for and did not get, and
whether they read the files the site publishes for them.

## Why it exists

Every claim in this workspace about how agents see our sites is currently an assumption. The
`agent-eligibility` check gives a rubric verdict; nobody has ever looked at whether an agent
turned up.

The specific question that prompted this tool: **is `llms.txt` being read by anyone?** The file
is published on `findmynextbite.food` and it is a young convention. Whether a single agent has
ever requested it is answerable from the server's own logs and by no other means.

There is a hard prerequisite, found on 2026-09-21: **the host does not currently keep access
logs.** Caddy is not configured to write them. Until that changes there is nothing to trace, so
this tool ships with that fact recorded rather than assumed away.

## Outcomes

1. **Observed visibility for our own sites.** A defensible answer to "are agents reading this",
   replacing an assumption with a count.
2. **A public tool others can run.** No dependency, a documented install, tests that run without
   special hardware.

## The claim boundary

`agenttrace` reports **what the log records**. The user-agent string is self-declared and
trivially spoofable, so an agent count is a count of *claims* to be that agent, and the tool says
so in its own output rather than presenting a visitor as verified.

It does **not** know about requests that never reached the server, cannot attribute business
value to a fetch, and does not infer that a page was read because it was served.

## What we are deliberately not doing

- **No live capture and no daemon.** It reads a file or standard input. Capturing is the web
  server's job, and a tool with its own process is a service, not a tool.
- **No IP addresses in the output.** The tool does not need them to answer any of its questions,
  and storing them creates an obligation nothing here justifies.
- **No external APIs and no accounts.** Standard library only.
- **No dashboard.** It prints a report and can emit JSON. Plotting is someone else's tool.

## What we reuse rather than rebuild

The log is the only input. It reads Caddy's JSON log format and the common/combined format most
servers write, so it is useful on a host it has never seen.

## Success, and what would stop us

- **Passes** when it answers "has any named AI agent fetched our pages this week" for a real
  host, from a real log.
- **Fails** if the answer is always zero because logging was never switched on — in which case
  the honest output is that fact, not a tool that looks like it is working.
- **Scope cap:** if the parser needs per-server configuration to be useful, stop and cut the
  supported formats to one rather than growing a configuration file.
