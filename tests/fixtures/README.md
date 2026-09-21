# Fixtures

Synthetic access logs. Nothing here was captured from a real server: the lines were
written by hand for `tests/`, and the addresses are documentation addresses from
RFC 5737 (`203.0.113.0/24`, `198.51.100.0/24`), apart from a few crawler ranges
(`66.249.66.1`, `40.77.167.1`, `17.58.0.1`, `74.6.0.1`) used to make the lines look
like the real thing. No real request, visitor or address is recorded.

| Fixture | What it is for |
| --- | --- |
| `caddy-sample.log` | Caddy JSON. 35 lines, 33 requests: four named agents, five search crawlers, other bots, browsers, two requests with no usable user-agent, one TLS runtime line and one truncated JSON line. `/llms.txt` **is** requested here, by GPTBot, with a 200 |
| `combined-sample.log` | The combined format with referer and user-agent. 13 lines, 13 requests, six named agents. `/llms.txt` is **not** requested, so it exercises the negative answer. One timestamp carries a `+0200` offset |
| `combined-common.log` | The common format: no referer and no user-agent at all, so every client is `unknown` |
| `caddy-all-agents.log` | One request from each of the twelve named agents, plus a Mozilla-prefixed `Applebot` and `Googlebot`, to pin the classification order |
| `caddy-no-agents.log` | Browsers, search crawlers and other bots only: the honest "no agent traffic" state |
| `malformed.log` | 6 lines, of which 2 are readable requests: a plain text line, a truncated JSON line, a bare request fragment and a blank line |
| `caddy-drifted.log` | Caddy-shaped JSON whose access fields are renamed (`request.path`, `status_code`): the refused-rather-than-guessed state |
| `caddy-llms-statuses.log` | `/llms.txt` answered 302, `/robots.txt` 304 and `/sitemap.xml` 403, by three named agents: the discovery verdicts that are not "read" |
| `combined-referer.log` | Apache's stock `referer` LogFormat and its `agent` variant: one trailing quoted field, plus a plain common line |
| `empty.log` | Zero bytes: the "cannot answer at all" state |
| `real-findmynextbite-2026-09-21-1828Z.log` | The one real extract, redacted under the registered rules; provenance in the `.md` beside it |

Counts asserted in the tests are hand counts of these files. If a fixture changes, the
numbers in `tests/test_report.py`, `tests/test_parse.py` and `tests/test_cli.py` change
with it — that is deliberate, because a fixture edit that quietly changes a count is
exactly the change worth noticing.
