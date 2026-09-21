# agenttrace

Give it a web server's access log; it reports what **claimed** AI agents asked for.

`agenttrace` reads a log the server already wrote — Caddy's JSON format, or the
common/combined format most other servers write, including Apache's stock `referer` and
`agent` variants and vhost-prefixed lines — and answers questions that only a log can answer:

- which named AI agents turned up, how often, for which paths, and with what status codes;
- whether they asked for `/robots.txt`, `/sitemap.xml` and **`/llms.txt`** — whether the last
  one is read at all is the question this tool exists to answer, so it is the first thing in
  the report;
- the paths agents asked for and **did not get** (404 and 410): a list of pages an agent
  wanted and the site does not have.

Python 3.11 or later. No dependencies, no accounts, no network calls, no daemon.

## Running it

```sh
# one log
python3 -m agenttrace /var/log/caddy/access.log

# several files, or a glob the shell does not expand
python3 -m agenttrace access.log access-2026-09-20.log
python3 -m agenttrace 'access-*.log'

# from a pipe (`--stdin`, or `-`)
zcat /var/log/caddy/access-*.log.gz | python3 -m agenttrace --stdin

# machine-readable
python3 -m agenttrace --json /var/log/caddy/access.log

# force a format when detection is wrong or the file is mixed
python3 -m agenttrace --format combined old-access.log

# declare your own client (a health check, a monitor) so it is set aside
# rather than counted as a bot or an agent; repeatable
python3 -m agenttrace --self FindMyNextBiteMonitor /var/log/caddy/access.log
```

On a host where the log belongs to the web server's user, you need to be able to read it:
`/var/log/caddy/*.log` is typically `0640` and owned by `caddy:caddy`, so either join the
`caddy` group (`sudo usermod -aG caddy "$USER"`, then a new login) or read it with `sudo`.
The tool itself needs no privileges and writes nothing.

Run it from this directory, or put this directory on `PYTHONPATH`.

### The JSON document

`--json` prints one document with these keys: `state` (`reported`, `no_agent_traffic` or
`no_readable_lines`), `claim_boundary`, `sources` (per file: line counts, detected format, and any
diagnostic), `coverage` (`first_seen`, `last_seen`, `duration_seconds`, `short_window`), `totals`
(`requests`, `by_category`, `named_agent_requests`, `agent_share`), `named_agents`,
`named_agents_not_seen`, `search_crawlers`, `declared_self` (the `--self` declarations, matched
and unmatched), `unrecognised_clients`, `dominant_client`, `discovery`, `top_agent_paths` and
`agent_missing_paths`.

In `discovery`, every count is named for what it counts: `named_agent_requests` and
`named_agent_statuses` are the twelve agents only, while `requests_from_all_clients` and
`statuses_from_all_clients` include every client. `served` is the honest boolean; `verdict`
carries the sentence.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | A report was produced. **Zero claimed agents is still a report** — read the notice, not just the code |
| 1 | A usage or input error: no input named, a path that does not exist, a directory, an unreadable file. The reason goes to stderr |
| 2 | The input opened but nothing in it was recognisable as an access-log line, so there is no report to give |

The 0/2 split is deliberate. "This log contains no agent requests" and "this file is not a log,
so I cannot answer" are different findings, and a script should be able to tell them apart.

## What the output looks like

```
agenttrace — what claimed AI agents asked a web server for

source  tests/fixtures/caddy-sample.log  (caddy)  35 lines, 33 read as requests, 2 not read as requests
coverage  2026-09-14T09:00:00Z .. 2026-09-14T14:01:40Z  (5.0 hours, 33 requests)

A user-agent string is self-declared and trivially spoofable. Every count below is a count
of claims to be that agent, not a count of verified agents.

Is /llms.txt being read?

  VERDICT: READ — 1 request from 1 named AI agent: GPTBot (200:1)

Discovery files requested by named AI agents

  /llms.txt     READ — 1 request from 1 named AI agent: GPTBot (200:1)
  /robots.txt   READ — 2 requests from 2 named AI agents: ClaudeBot (200:1), GPTBot (200:1)
  /sitemap.xml  READ — 1 request from 1 named AI agent: GPTBot (200:1)

Named AI agents — 4 of 12 seen

  agent          requests  paths  first seen            last seen             statuses
  GPTBot                7      7  2026-09-14T09:00:00Z  2026-09-14T09:00:30Z  200:6 404:1
  ClaudeBot             3      3  2026-09-14T10:00:00Z  2026-09-14T10:00:10Z  200:2 404:1
  PerplexityBot         2      2  2026-09-14T11:00:00Z  2026-09-14T11:00:05Z  200:2
  ChatGPT-User          1      1  2026-09-14T12:00:00Z  2026-09-14T12:00:00Z  200:1
  not seen in this log: OAI-SearchBot, Claude-User, Perplexity-User, Google-Extended, CCBot,
  Applebot-Extended, Bytespider, meta-externalagent

Search crawlers seen

  agent        requests  paths  first seen            last seen             statuses
  Googlebot           3      3  2026-09-14T12:20:00Z  2026-09-14T12:20:20Z  200:2 410:1
  Bingbot             2      2  2026-09-14T12:36:40Z  2026-09-14T12:36:50Z  200:2
  Applebot            1      1  2026-09-14T13:10:00Z  2026-09-14T13:10:00Z  200:1
  DuckDuckBot         1      1  2026-09-14T12:53:20Z  2026-09-14T12:53:20Z  200:1
  Slurp               1      1  2026-09-14T13:10:05Z  2026-09-14T13:10:05Z  200:1

Unrecognised user agents (top 5)

         1  (no user-agent)
         1  -
  These matched no rule and no --self declaration. Read them before drawing a conclusion
  from the counts above: a site's own monitor, a status checker or a client library lands
  here.

Site-wide

  requests in this log                   33
  claimed by a named AI agent            13  (39.4%)
  search crawler                        8  (24.2%)
  other bot                             6  (18.2%)
  browser                               4  (12.1%)
  unrecognised                          2  (6.1%)

Top paths fetched by named AI agents (top 10)

     2  /robots.txt
     2  /recipes/black-bean-tacos
     2  /recipes/miso-soup
     2  /pricing
     1  /sitemap.xml
     1  /llms.txt
     1  /recipes/vegan-carbonara
     1  /about
     1  /

Paths named AI agents asked for and did not get (404, 410)

     1  /about  (404:1; ClaudeBot)
     1  /recipes/vegan-carbonara  (404:1; GPTBot)
```

**"READ" has a precise meaning in that block**: a named agent requested the file and the log
records a 2xx status. A `304 Not Modified` is read as read, because the client's copy was
current, and says so. A `301`/`302` is **not** read — the file itself was not served at that
path — and neither is a 404, a 410, a 403 or a request that produced no status at all.

The named agents are `GPTBot`, `OAI-SearchBot`, `ChatGPT-User`, `ClaudeBot`, `Claude-User`,
`PerplexityBot`, `Perplexity-User`, `Google-Extended`, `CCBot`, `Applebot-Extended`,
`Bytespider` and `meta-externalagent`. Everything else that identifies itself is counted as a
search crawler, another bot, a browser, or unrecognised.

### The first real window

`agenttrace --self FindMyNextBiteMonitor var/findmynextbite-access.log`, over 42 requests on
2026-09-21, is what the tool says about a real server — and it is also the clearest example of
why every count in it is a count of *claims*:

```
coverage  2026-09-21T18:28:02Z .. 2026-09-21T18:36:32Z  (8.5 minutes, 42 requests)

Is /llms.txt being read?

  VERDICT: READ — 1 request from 1 named AI agent: GPTBot (200:1)

Set aside — declared your own (--self)

        38  FindMyNextBiteMonitor  (32 path(s))

Site-wide

  requests in this log                   42
  claimed by a named AI agent             1  (2.4%)
  other bot                               2  (4.8%)
  browser                                 1  (2.4%)
  declared your own                      38  (90.5%)
```

The tool is right about the bytes: a request carrying the `GPTBot` string did ask for
`/llms.txt` and got a 200. The claim was false — the site's operator had generated it with
`curl -A "…GPTBot/1.2…"` minutes earlier, to prove the logging he had just switched on was
working. **Zero external AI agents appear in that window**, and the only named-agent line in it
is an artefact of the change that enabled the observation. That is the whole reason the report
says *claims* and prints the window's duration: a 510-second sample, taken while somebody was at
the keyboard, cannot tell you what a week looks like.

## When there is nothing to report

A log with no agent requests does not get a report of zeros. It gets this:

```
NO NAMED AI AGENT TRAFFIC IN THIS LOG

8 request(s) were read, and none claimed to be one of the 12 named AI agents. This is not a
report that no agent visited: it says this log contains no such claim, and a server that is
not logging at all produces exactly this picture.

agenttrace was written for a host that kept none — findmynextbite.food kept none until
2026-09-21 — so a zero from a host with logging switched off says nothing about agents.
README.md shows how to switch it on in Caddy.
```

A zero from a server that writes no log means nothing at all. That is why the tool says so
instead of printing an empty table, and why it exits 2 rather than 0 when the input is not a
log at all. In `--json` mode the same finding appears as `"state": "no_agent_traffic"` or
`"state": "no_readable_lines"`, with a `notice` explaining it.

## What it does not do

- **It does not verify anything.** A user-agent string is chosen by the client and is trivial
  to forge, so every count is a count of *claims*. A page being served is not evidence it was
  read, and a request that never reached the server is invisible here.
- **It never reads or prints a client address.** The address field the log may contain is not
  extracted by either parser, and a test asserts that no fixture address can appear in either
  output mode. You do not need addresses to answer any question the report asks.
- **It does not capture traffic.** No daemon, no proxy, no dashboard, no external API. It
  reads a file or standard input and stops.
- **It has no time window.** There is no `--since`/`--until`; the report covers exactly the
  log you give it, and prints the first and last request it saw so you can tell what that
  covers. For "this week", feed it the rotated files that cover the week.
- **It does not read gzip.** Caddy compresses rolled logs by default, so pipe them through
  `zcat` as shown above.
- **It is not configurable per server.** Two formats, auto-detected. If a third server cannot
  be read without its own configuration, the supported set shrinks rather than growing a
  config file. A changed schema is refused with the fields it saw and the fields it expected,
  rather than guessed at.
- **It does not decide who is a bot for you.** A site's own monitor is usually the loudest
  client in its log. When one undeclared client holds most of the log the report says so, by
  name, and says the tool cannot tell whether it is yours; `--self` is how you tell it.

## Switching access logging on in Caddy

This is the step that makes the tool useful. It is the host's decision, not the tool's: the
site `findmynextbite.food` currently keeps no access log, so agenttrace cannot answer its own
question there.

If you run Caddy 2, add a `log` block to the site (the [Caddy `log` directive
documentation](https://caddyserver.com/docs/caddyfile/directives/log) is the authority here):

```caddyfile
findmynextbite.food {
	# ... your existing directives ...

	log {
		output file /var/log/caddy/findmynextbite-access.log {
			# Rotation is on by default; these are the defaults made explicit.
			roll_size 100MiB
			roll_keep 10
		}

		# JSON is what Caddy writes to a file by default; asking for it is harmless
		# and makes the format explicit. A filter wraps it to drop the address fields.
		format filter {
			wrap json
			request>remote_ip delete
			request>client_ip delete
		}
	}
}
```

Notes that matter before you enable it:

- **The log would otherwise store client addresses.** Caddy records `request>remote_ip` (and,
  since v2.7, `request>client_ip`) on every access line. agenttrace never reads either field,
  but the file is still a store of addresses — so delete them as above, or truncate them with
  an `ip_mask` filter (`request>remote_ip ip_mask 16 32` keeps the network and drops the
  host). Caddy already redacts `Cookie`, `Set-Cookie` and `Authorization` by default.
- **Watch the disk.** Rotation, `roll_keep` and compression are the defaults; check they suit
  the volume you get. Rolled files are named `<name>-<timestamp>-<reason>.log` and compressed
  to `.gz`.
- **A restart is required** for a change to an output file to take effect — a reload is not
  enough, unless you change the filename.
- **The directory must exist** and be writable by the user Caddy runs as
  (`mkdir -p /var/log/caddy`), and the log will grow on the volume that holds it.
- **Check it is working** before pointing agenttrace at it:
  `tail -n 1 /var/log/caddy/findmynextbite-access.log` should show a request line.

```sh
python3 -m agenttrace /var/log/caddy/findmynextbite-access.log
```

## Tests

```sh
make ci     # the record check, then the project checks
make test   # byte-compile the package, then run the tests
python3 -m unittest discover -s tests -t .
```

The tests are driven by the logs in `tests/fixtures/` (see
[`tests/fixtures/README.md`](tests/fixtures/README.md)) — synthetic ones, plus one small
redacted extract of the host's real log, whose provenance and redaction rules are recorded
beside it. They make no network call and read nothing outside this repository. The choices behind the tool, with the measurements taken for
them, are in [`docs/DESIGN.md`](docs/DESIGN.md); the project's decision record is
[`RECORD.md`](RECORD.md).
